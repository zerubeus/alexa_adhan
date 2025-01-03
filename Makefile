.PHONY: create-skill build-lambda deploy-lambda deploy-skill deploy aws-login

aws-login:
	aws sso login --profile zerbania

create-skill:
	ask create-skill \
			--profile default \
			--manifest ./skill-package/skill.json \
			--hosting-provider lambda

build-lambda:
	sam build --use-container

deploy-lambda:
	sam deploy

deploy-skill:
    $(eval LAMBDA_ARN := $(shell aws cloudformation describe-stacks \
        --stack-name zerubeus-alexa-adhan \
        --query 'Stacks[0].Outputs[?OutputKey==`PrayerTimesFunctionArn`].OutputValue' \
        --output text \
        --region eu-west-1 \
        --profile zerbania))

    ask deploy

    $(eval SKILL_ID := $(shell jq -r '.profiles.default.skillId' .ask/ask-states.json))
    
    aws lambda add-permission \
        --function-name $(LAMBDA_ARN) \
        --statement-id "AlexaSkill_$(SKILL_ID)" \
        --action lambda:InvokeFunction \
        --principal alexa-appkit.amazon.com \
        --event-source-token $(SKILL_ID) \
        --region eu-west-1 \
        --profile zerbania

deploy: build-lambda deploy-lambda deploy-skill