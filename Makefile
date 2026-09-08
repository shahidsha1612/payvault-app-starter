# PayVault starter — convenience targets.
# All AWS actions target a SANDBOX profile. Never use a real/prod account.

AWS_PROFILE ?= default
TF          := terraform -chdir=terraform
export AWS_PROFILE

.PHONY: help score deploy test destroy fmt init advisory

help:
	@echo "PayVault starter targets:"
	@echo "  make score                 - run the deterministic self-evaluation"
	@echo "  make advisory              - score + run opa/terraform if installed (not graded)"
	@echo "  make deploy  AWS_PROFILE=x  - terraform init + apply into a sandbox"
	@echo "  make test    AWS_PROFILE=x  - POST a fake charge to the deployed API"
	@echo "  make destroy AWS_PROFILE=x  - tear the sandbox down"

score:
	python3 scoring/score.py

advisory:
	python3 scoring/score.py --advisory

init:
	$(TF) init

deploy: init
	$(TF) apply -auto-approve

test:
	@API=$$($(TF) output -raw api_endpoint); \
	echo "POSTing a fake charge to $$API/charge"; \
	API=$$API ./test/smoke.sh

destroy:
	$(TF) destroy -auto-approve

fmt:
	$(TF) fmt -recursive
