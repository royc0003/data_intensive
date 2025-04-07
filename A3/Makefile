# Variables
DOCKER_REGISTRY = royc003
NAMESPACE = bookstore-ns
SERVICES = book-service bff-web bff-mobile customer-service crm-service

# Build Docker images
build:
	@echo "Building Docker images..."
	# Move to the parent directory to execute the build commands
	cd bff-web && docker build -f Dockerfile.web-bff -t ${DOCKER_REGISTRY}/bookstore-api:1 ..
	cd bff-mobile && docker build -f Dockerfile.mobile-bff -t ${DOCKER_REGISTRY}/bookstore-api:2 ..
	# cd customer-service && docker build -f Dockerfile.customer-service -t ${DOCKER_REGISTRY}/bookstore-api:3 ..
	# cd book-service && docker build -f Dockerfile.book-service -t ${DOCKER_REGISTRY}/bookstore-api:4 ..

push:
	docker push ${DOCKER_REGISTRY}/bookstore-api:1
	docker push ${DOCKER_REGISTRY}/bookstore-api:2
	# docker push ${DOCKER_REGISTRY}/bookstore-api:3
	# docker push ${DOCKER_REGISTRY}/bookstore-api:4

# Apply Kubernetes configuration files
apply: build
	@echo "Applying Kubernetes configs..."
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f bff-web/k8s/deployment.yaml
	kubectl apply -f bff-web/k8s/service.yaml
	kubectl apply -f bff-mobile/k8s/deployment.yaml
	kubectl apply -f bff-mobile/k8s/service.yaml
	# kubectl apply -f book-service/k8s/deployment.yaml
	# kubectl apply -f book-service/k8s/service.yaml
	# kubectl apply -f customer-service/k8s/deployment.yaml
	# kubectl apply -f customer-service/k8s/service.yaml
	# kubectl apply -f crm-service/k8s/deployment.yaml
	# kubectl apply -f crm-service/k8s/service.yaml

# Get service URLs (useful for checking EXTERNAL-IP)
get-urls:
	@echo "Fetching service URLs..."
	kubectl get services -n $(NAMESPACE)

# Port forward (optional for local testing)
port-forward:
	@echo "Forwarding ports to local machine..."
	kubectl port-forward service/book-service 3000:3000 -n $(NAMESPACE) &
	kubectl port-forward service/bff-web 80:80 -n $(NAMESPACE) &
	kubectl port-forward service/bff-mobile 80:80 -n $(NAMESPACE) &

# Clean up Kubernetes resources
clean:
	@echo "Cleaning up Kubernetes resources..."
	kubectl delete -f k8s/
	kubectl delete -f bff-web/k8s/
	kubectl delete -f bff-mobile/k8s/
	kubectl delete -f customer-service/k8s/
	kubectl delete -f crm-service/k8s/
	kubectl delete -f book-service/k8s/

.PHONY: build apply get-urls port-forward clean
