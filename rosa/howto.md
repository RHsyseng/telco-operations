Here are the steps I used for Rosa evaluation

# Requisites

### Prepare your account

enable ROSA marketplace offering from [https://aws.amazon.com/marketplace/pp/prodview-wxwneoj4tppqo](https://aws.amazon.com/marketplace/pp/prodview-wxwneoj4tppqo)

Note: for using stage, a mail needs to be sent first to `jfiala@redhat.com` specifying aws account id to enable for stage and then enable from [https://aws.amazon.com/marketplace/pp/B08GH6FMHC](https://aws.amazon.com/marketplace/pp/B08GH6FMHC)

### Put valid creds in $HOME/.aws/credentials

```
[default]
aws_access_key_id = XXXX
aws_secret_access_key = XXXX
```

###  Get aws cli

```
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
/usr/local/bin/aws --version
```

### Get rosa cli

```
curl https://mirror.openshift.com/pub/openshift-v4/clients/rosa/latest/rosa-linux.tar.gz  > rosa-linux.tar.gz
tar xvf rosa-linux.tar.gz
mv rosa /usr/local/bin/rosa
chmod u+x /usr/local/bin/rosa
rosa completion bash > /etc/bash_completion.d/rosa
```

# Create cluster

## get valid token

from [https://console.redhat.com/openshift/token/rosa](https://console.redhat.com/openshift/token/rosa)

## Launch deployment


```
export ROSA_TOKEN=$(cat rosa_token.txt)
rosa login
rosa create account-roles --mode auto
rosa create cluster --cluster-name testrosa1 --sts --mode auto
```

## Create admin user

```
rosa create admin --cluster=testrosa1
```

You can then login using the output from this command

## Follow cluster install

```
rosa logs install -c testrosa1 --watch
```

## Delete cluster

```
rosa delete cluster -c testrosa1
```

# Deploy a private hosted cluster

## Create a dedicated vpc and a private subnet

Using kcli:

```
kcli create network -P cidr=15.0.0.0/16 -P subnet_cidr=15.0.1.0/24 rosanetwork
kcli create subnet -P network=rosanetwork -c 15.0.2.0/24 -i rosanetwork-subnet2
SUBNET_ID=$(kcli info subnet rosanetwork-subnet2  | grep SubnetId | cut -d: -f2 | xargs)
```

Alternatively, terraform can be used from https://github.com/openshift-cs/terraform-vpc-example

## Create cluster

Note the use of additional hosted-cp, private and subnet-ids flags

```
rosa create cluster --sts --cluster-name testrosa2 --hosted-cp --private --subnet-ids $SUBNET_ID --region=us-east-2 --mode=auto --machine-cidr 15.0.0.0/16
```

# References

- [https://docs.openshift.com/rosa/rosa_hcp/rosa-hcp-sts-creating-a-cluster-quickly.html](https://docs.openshift.com/rosa/rosa_hcp/rosa-hcp-sts-creating-a-cluster-quickly.html)
