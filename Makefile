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
	$(eval SKILL_ID := $(shell jq -r '.profiles.default.skillId' .ask/ask-states.json))
	sam deploy --parameter-overrides SkillId=$(SKILL_ID)

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

deploy: build-lambda deploy-lambda deploy-skill