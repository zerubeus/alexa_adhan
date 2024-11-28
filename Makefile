.PHONY: build-PrayerTimesFunctionLayers deploy-skill

build-PrayerTimesFunctionLayers:
    mkdir -p "$(ARTIFACTS_DIR)/python"
    python -m pip install -r requirements.txt -t "$(ARTIFACTS_DIR)/python"

deploy-skill:
    $(eval LAMBDA_ARN := $(shell aws cloudformation describe-stacks \
        --stack-name zerubeus-alexa-adhan \
        --query 'Stacks[0].Outputs[?OutputKey==`PrayerTimesFunctionArn`].OutputValue' \
        --output text))
    
    ask deploy --force
    
    $(eval SKILL_ID := $(shell jq -r '.skillId' .ask/ask-states.json))
    
    aws lambda add-permission \
        --function-name $(LAMBDA_ARN) \
        --statement-id "AlexaSkill_$(SKILL_ID)" \
        --action lambda:InvokeFunction \
        --principal alexa-appkit.amazon.com \
        --event-source-token $(SKILL_ID)
    
    @echo "Skill deployed and linked successfully!"

deploy: build-PrayerTimesFunctionLayers
    sam deploy
    make deploy-skill