install:
	pip3 install -r requirements.txt

test:
	python3 -m pytest tests/ -v

local:
	python3 -m uvicorn app.main:app --reload --port 8000

package:
	rm -rf package/ lambda.zip
	mkdir -p package
	docker run --rm \
		--platform linux/amd64 \
		-v $(PWD):/var/task \
		public.ecr.aws/sam/build-python3.11 \
		pip install -r requirements.txt -t package/
	cp -r app package/
	cd package && zip -r ../lambda.zip . && cd ..
	rm -rf package/
	@echo "✅ lambda.zip ready"

deploy: package
	cd infra && terraform init && terraform apply -auto-approve

clean:
	rm -rf package/ lambda.zip __pycache__ .pytest_cache

.PHONY: install test local package deploy clean
