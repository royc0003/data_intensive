bookstore-app/
├── book-service/
│   ├── app/                         # Your FastAPI code
│   ├── Dockerfile
│   └── k8s/
│       ├── deployment.yaml
│       └── service.yaml

├── customer-service/
│   ├── app/
│   ├── Dockerfile
│   └── k8s/
│       ├── deployment.yaml
│       └── service.yaml

├── bff-web/
│   ├── app/
│   ├── Dockerfile
│   └── k8s/
│       ├── deployment.yaml
│       └── service.yaml

├── crm-service/
│   ├── app/
│   ├── Dockerfile
│   └── k8s/
│       ├── deployment.yaml

├── k8s/                             # Global/shared configs
│   └── namespace.yaml
│   └── secrets.yaml  # optional

└── README.md

