.PHONY: create-skill build-lambda deploy-lambda deploy-skill deploy aws-login upload-media

aws-login:
	aws sso login --profile zerbania

create-skill:
	ask create-skill \
			--profile default \
			--manifest ./skill-package/skill.json

build-lambda:
	cd lambda && poetry install --no-root && cd .. && sam build --use-container

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
