#!/bin/bash

# Copy all files from the current directory to the remote server
# scp -i /path/to/key.pem /path/to/local/file ec2-user@your-ec2-ip:/destination/path
# Copy current make file
scp -i $(PWD)/labsuser.pem $(PWD)/Makefile ec2-user@ec2-13-216-70-18.compute-1.amazonaws.com:/home/ec2-user
# Copy all k8s files
scp -i $(PWD)/labsuser.pem $(PWD)/k8s/* ec2-user@ec2-13-216-70-18.compute-1.amazonaws.com:/home/ec2-user/k8s
# Copy all bff-web k8s files
scp -i $(PWD)/labsuser.pem $(PWD)/bff-web/k8s/* ec2-user@ec2-13-216-70-18.compute-1.amazonaws.com:/home/ec2-user/bff-web/k8s
# Copy all bff-mobile k8s files
scp -i $(PWD)/labsuser.pem $(PWD)/bff-mobile/k8s/* ec2-user@ec2-13-216-70-18.compute-1.amazonaws.com:/home/ec2-user/bff-mobile/k8s
# Copy all customer-service k8s files
scp -i $(PWD)/labsuser.pem $(PWD)/customer-service/k8s/* ec2-user@ec2-13-216-70-18.compute-1.amazonaws.com:/home/ec2-user/customer-service/k8s
# Copy all book-service k8s files
scp -i $(PWD)/labsuser.pem $(PWD)/book-service/k8s/* ec2-user@ec2-13-216-70-18.compute-1.amazonaws.com:/home/ec2-user/book-service/k8s
# Copy all crm-service k8s files
scp -i $(PWD)/labsuser.pem $(PWD)/crm-service/k8s/* ec2-user@ec2-13-216-70-18.compute-1.amazonaws.com:/home/ec2-user/crm-service/k8s
