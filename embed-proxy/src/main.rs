use axum::{
    Json, Router,
    body::Body,
    extract::{Request, State},
    http::{HeaderMap, StatusCode},
    middleware::Next,
    response::{IntoResponse, Response},
    routing::{get, post},
};
use reqwest::Client;
use serde::Serialize;
use std::{collections::HashMap, env, net::SocketAddr, sync::Arc, time::Duration};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

const MODEL_HEADER: &str = "x-embed-model";

#[derive(Clone)]
struct Config {
    base_domain: String,
    use_https: bool,
    connect_timeout: Duration,
    request_timeout: Duration,
    models: HashMap<String, String>,
}

impl Config {
    fn from_env() -> Self {
        let base_domain = env::var("EMBED_BASE_DOMAIN").unwrap_or_else(|_| "fly.dev".to_string());

        // Use HTTPS for .fly.dev, HTTP for .internal
        let use_https = !base_domain.ends_with(".internal");

        let connect_timeout = env::var("CONNECT_TIMEOUT_SECS")
            .ok()
            .and_then(|s| s.parse().ok())
            .map(Duration::from_secs)
            .unwrap_or(Duration::from_secs(10));

        let request_timeout = env::var("REQUEST_TIMEOUT_SECS")
            .ok()
            .and_then(|s| s.parse().ok())
            .map(Duration::from_secs)
            .unwrap_or(Duration::from_secs(300));

        let models: HashMap<String, String> = [
            ("bge-small", "embed-bge-small"),
            ("bge-base", "embed-bge-base"),
            ("bge-large", "embed-bge-large"),
            ("bge-m3", "embed-bge-m3"),
        ]
        .into_iter()
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .collect();

        Self {
            base_domain,
            use_https,
            connect_timeout,
            request_timeout,
            models,
        }
    }

    fn get_backend_url(&self, model: &str, path: &str) -> Option<String> {
        self.models.get(model).map(|app_name| {
            let scheme = if self.use_https { "https" } else { "http" };
            format!("{}://{}.{}{}", scheme, app_name, self.base_domain, path)
        })
    }

    fn valid_models(&self) -> Vec<&str> {
        self.models.keys().map(|s| s.as_str()).collect()
    }
}

#[derive(Clone)]
struct AppState {
    client: Client,
    config: Arc<Config>,
}

#[derive(Debug)]
enum AppError {
    MissingHeader(String),
    InvalidModel { model: String, valid: Vec<String> },
    BackendError(String),
}

#[derive(Serialize)]
struct ErrorResponse {
    error: ErrorBody,
}

#[derive(Serialize)]
struct ErrorBody {
    message: String,
    #[serde(rename = "type")]
    error_type: String,
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, error_type, message) = match self {
            AppError::MissingHeader(header) => (
                StatusCode::BAD_REQUEST,
                "invalid_request_error",
                format!("Missing required header: {}", header),
            ),
            AppError::InvalidModel { model, valid } => (
                StatusCode::BAD_REQUEST,
                "invalid_request_error",
                format!(
                    "Invalid model '{}'. Valid models: {}",
                    model,
                    valid.join(", ")
                ),
            ),
            AppError::BackendError(msg) => (
                StatusCode::BAD_GATEWAY,
                "backend_error",
                format!("Backend error: {}", msg),
            ),
        };

        let body = ErrorResponse {
            error: ErrorBody {
                message,
                error_type: error_type.to_string(),
            },
        };

        (status, Json(body)).into_response()
    }
}

async fn proxy_handler(
    State(state): State<AppState>,
    headers: HeaderMap,
    request: Request,
) -> Result<Response, AppError> {
    let model = headers
        .get(MODEL_HEADER)
        .and_then(|v| v.to_str().ok())
        .ok_or_else(|| AppError::MissingHeader(MODEL_HEADER.to_string()))?;

    let path = request.uri().path();

    let backend_url =
        state
            .config
            .get_backend_url(model, path)
            .ok_or_else(|| AppError::InvalidModel {
                model: model.to_string(),
                valid: state
                    .config
                    .valid_models()
                    .iter()
                    .map(|s| s.to_string())
                    .collect(),
            })?;

    tracing::info!(model = model, path = path, backend = %backend_url, "Proxying request");

    let content_type = headers
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("application/json");

    let body_bytes = axum::body::to_bytes(request.into_body(), usize::MAX)
        .await
        .map_err(|e| AppError::BackendError(format!("Failed to read request body: {}", e)))?;

    let response = state
        .client
        .post(&backend_url)
        .header("content-type", content_type)
        .body(body_bytes)
        .send()
        .await
        .map_err(|e| AppError::BackendError(e.to_string()))?;

    let status = response.status();
    let response_headers = response.headers().clone();

    let body_bytes = response
        .bytes()
        .await
        .map_err(|e| AppError::BackendError(format!("Failed to read response: {}", e)))?;

    let mut builder = Response::builder().status(status);

    for (name, value) in response_headers.iter() {
        let name_str = name.as_str();
        if name_str.starts_with("content-")
            || name_str.starts_with("x-")
            || name_str == "x-request-id"
        {
            builder = builder.header(name, value);
        }
    }

    Ok(builder.body(Body::from(body_bytes)).unwrap())
}

async fn auth_middleware(request: Request, next: Next) -> Response {
    // TODO: Implement authentication
    // Example future implementation:
    //
    // let auth_header = request.headers().get("authorization");
    // match auth_header {
    //     Some(token) if validate_token(token) => next.run(request).await,
    //     Some(_) => StatusCode::UNAUTHORIZED.into_response(),
    //     None => StatusCode::UNAUTHORIZED.into_response(),
    // }

    next.run(request).await
}

async fn health() -> &'static str {
    "OK"
}

#[tokio::main]
async fn main() {
    tracing_subscriber::registry()
        .with(tracing_subscriber::fmt::layer())
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "embed_proxy=info".parse().unwrap()),
        )
        .init();

    let config = Config::from_env();

    tracing::info!(
        base_domain = %config.base_domain,
        use_https = config.use_https,
        connect_timeout_secs = config.connect_timeout.as_secs(),
        request_timeout_secs = config.request_timeout.as_secs(),
        "Starting embed-proxy"
    );

    let client = Client::builder()
        .connect_timeout(config.connect_timeout)
        .timeout(config.request_timeout)
        .pool_max_idle_per_host(10)
        .build()
        .expect("Failed to create HTTP client");

    let state = AppState {
        client,
        config: Arc::new(config),
    };

    let app = Router::new()
        .route("/embed", post(proxy_handler))
        .route("/v1/embeddings", post(proxy_handler))
        .route("/health", get(health))
        .layer(axum::middleware::from_fn(auth_middleware))
        .with_state(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    tracing::info!("Listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
