.PHONY: create-skill build-lambda deploy-lambda deploy-skill deploy aws-login upload-media release

aws-login:
	aws sso login --profile zerbania

create-skill:
	ask create-skill \
			--profile default \
			--manifest ./skill-package/skill.json

build-lambda:
	poetry install --no-root
	poetry export --without-hashes > lambda_layers/prayer_times_functions_layers/requirements.txt
	sam build --use-container

deploy-lambda:
	$(eval SKILL_ID := $(shell jq -r '.profiles.default.skillId' .ask/ask-states.json))
	sam deploy --parameter-overrides SkillId=$(SKILL_ID) --no-fail-on-empty-changeset

deploy-skill:
	@echo "Getting Lambda function ARN..."
	$(eval LAMBDA_ARN := $(shell aws cloudformation describe-stack-resources \
			--stack-name zerubeus-alexa-adhan \
			--query "StackResources[?ResourceType=='AWS::Lambda::Function'].PhysicalResourceId" \
			--output text \
			--region eu-west-1 \
			--profile zerbania))

	@echo "Found Lambda ARN: $(LAMBDA_ARN)"

	@if [ -z "$(LAMBDA_ARN)" ]; then \
			echo "Error: Could not retrieve Lambda ARN from CloudFormation stack"; \
			exit 1; \
	fi

	ask deploy

upload-media:
	@echo "Getting S3 bucket name…"
	$(eval BUCKET_NAME := $(shell aws cloudformation describe-stack-resources \
		--stack-name zerubeus-alexa-adhan \
		--query "StackResources[?LogicalResourceId=='AthanAudioBucket'].PhysicalResourceId" \
		--output text \
		--region eu-west-1 \
		--profile zerbania))
	@echo "Found S3 bucket: $(BUCKET_NAME)"
	aws s3 sync ./media s3://$(BUCKET_NAME) --delete --profile zerbania

deploy: build-lambda deploy-lambda upload-media deploy-skill

release:
	@# Get the latest tag, default to v0.0.0 if no tags exist
	$(eval LATEST_TAG := $(shell git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0"))
	@echo "Latest tag: $(LATEST_TAG)"
	
	@# Extract version numbers and increment patch version
	$(eval MAJOR := $(shell echo $(LATEST_TAG) | sed 's/v\([0-9]*\).\([0-9]*\).\([0-9]*\)/\1/'))
	$(eval MINOR := $(shell echo $(LATEST_TAG) | sed 's/v\([0-9]*\).\([0-9]*\).\([0-9]*\)/\2/'))
	$(eval PATCH := $(shell echo $(LATEST_TAG) | sed 's/v\([0-9]*\).\([0-9]*\).\([0-9]*\)/\3/'))
	$(eval NEW_PATCH := $(shell echo $$(($(PATCH) + 1))))
	$(eval NEW_VERSION := v$(MAJOR).$(MINOR).$(NEW_PATCH))
	
	@echo "Creating new release $(NEW_VERSION)..."
	
	@# Check if this is the first release
	$(eval IS_FIRST_RELEASE := $(shell git tag -l | wc -l | tr -d ' '))
	
	@# Collect commit messages since last tag or all commits if first release
	$(eval COMMIT_LOG := $(shell if [ "$(IS_FIRST_RELEASE)" -eq "0" ]; then \
		git log --pretty=format:"- %s"; \
	else \
		git log $(LATEST_TAG)..HEAD --pretty=format:"- %s"; \
	fi))
	
	@if [ -z "$(COMMIT_LOG)" ]; then \
		echo "No new commits since last release $(LATEST_TAG)"; \
		exit 1; \
	fi
	
	@# Create annotated tag with commit messages
	git tag -a $(NEW_VERSION) -m "Release $(NEW_VERSION)" -m "Changes since $(LATEST_TAG):" -m "$(COMMIT_LOG)"
	git push origin $(NEW_VERSION)
	
	@echo "Release $(NEW_VERSION) created and pushed successfully"
	@echo "Changes included in this release:"
	@echo "$(COMMIT_LOG)"
	@echo "\nCreating GitHub release..."
	gh release create $(NEW_VERSION) --notes "$(COMMIT_LOG)"
	@echo "GitHub release created successfully"