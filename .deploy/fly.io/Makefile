.PHONY: help generate list deploy deploy-all status logs destroy

# Default target
help:
	@echo "TEI Server Deployment Commands"
	@echo ""
	@echo "  make generate        Generate fly.toml configs from config.yaml"
	@echo "  make list            List all configured apps"
	@echo "  make deploy APP=x    Deploy a specific app"
	@echo "  make deploy-all      Deploy all apps"
	@echo "  make status          Show status of all deployed apps"
	@echo "  make logs APP=x      View logs for an app"
	@echo "  make destroy APP=x   Destroy an app (with confirmation)"
	@echo ""

# Generate fly.toml files from config
generate:
	@ROOT_DIR=$(CURDIR) ./scripts/generate-configs.sh

# List all apps defined in config
list:
	@if [ -d apps ]; then \
		echo "Configured apps:"; \
		for app in apps/*/; do \
			if [ -d "$$app" ]; then \
				echo "  - $$(basename $$app)"; \
			fi; \
		done; \
	else \
		echo "No apps generated yet. Run 'make generate' first."; \
	fi

# Deploy a specific app
deploy:
ifndef APP
	@echo "Error: APP is required. Usage: make deploy APP=embed-bge-base"
	@exit 1
endif
	@./scripts/deploy.sh $(APP)

# Deploy all apps
deploy-all: generate
	@for app in apps/*/; do \
		if [ -d "$$app" ]; then \
			./scripts/deploy.sh "$$(basename $$app)"; \
		fi; \
	done

# Show status of all apps
status:
	@echo "Checking app status..."
	@for app in apps/*/; do \
		if [ -d "$$app" ]; then \
			name=$$(basename $$app); \
			echo ""; \
			echo "=== $$name ==="; \
			fly status --app $$name 2>/dev/null || echo "  Not deployed"; \
		fi; \
	done

# View logs for an app
logs:
ifndef APP
	@echo "Error: APP is required. Usage: make logs APP=embed-bge-base"
	@exit 1
endif
	fly logs --app $(APP)

# Destroy an app
destroy:
ifndef APP
	@echo "Error: APP is required. Usage: make destroy APP=embed-bge-base"
	@exit 1
endif
	@echo "This will destroy $(APP) and all its data."
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] && fly apps destroy $(APP) --yes || echo "Cancelled"
