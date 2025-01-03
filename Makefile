.PHONY: create-skill build-lambda deploy-lambda deploy-skill deploy aws-login

aws-login:
	aws sso login --profile zerbania

create-skill:
	ask create-skill \
			--profile default \
			--manifest ./skill-package/skill.json

build-lambda:
	sam build --use-container

deploy-lambda:
	sam deploy

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

	$(eval SKILL_ID := $(shell jq -r '.profiles.default.skillId' .ask/ask-states.json))
	$(eval STATEMENT_ID := $(shell echo "AlexaSkill_$(SKILL_ID)" | sed 's/[^a-zA-Z0-9_-]/_/g'))

	@echo "Checking existing permissions for statement ID: $(STATEMENT_ID)"

	$(eval EXISTING_STATEMENT := $(shell \
		aws lambda get-policy \
			--function-name "$(LAMBDA_ARN)" \
			--region eu-west-1 \
			--profile zerbania 2>/dev/null | \
		jq -r '.Policy | fromjson.Statement[]? | select(.Sid=="$(STATEMENT_ID)") | .Sid' \
		|| true \
	))

	@if [ -z "$(EXISTING_STATEMENT)" ]; then \
		echo "Adding permission to lambda function $(LAMBDA_ARN) for skill $(SKILL_ID)"; \
		aws lambda add-permission \
			--function-name "$(LAMBDA_ARN)" \
			--statement-id "$(STATEMENT_ID)" \
			--action lambda:InvokeFunction \
			--principal alexa-appkit.amazon.com \
			--event-source-token "$(SKILL_ID)" \
			--region eu-west-1 \
			--profile zerbania; \
	else \
		echo "Permission statement '$(STATEMENT_ID)' already exists. Skipping add-permission."; \
	fi

deploy: build-lambda deploy-lambda deploy-skill