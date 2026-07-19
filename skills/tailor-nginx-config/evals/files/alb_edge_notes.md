# Topology for ALB trust-boundary eval

- Public TLS terminates at AWS ALB.
- ALB forwards HTTP to EC2 Nginx on port 80.
- FastAPI listens on 127.0.0.1:8000 behind Nginx.
- ALB VPC CIDR for real_ip trust (example): 10.0.0.0/16
- Do not trust arbitrary client-supplied X-Forwarded-\* at the public edge.
