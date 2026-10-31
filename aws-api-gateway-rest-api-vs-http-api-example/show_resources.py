"""Expand each SAM template offline and list the CloudFormation resources it creates.

Uses the AWS SAM translator (the same library sam validate and sam deploy use),
so we can see what each API type turns into without an AWS account.
Usage: python show_resources.py template-rest.yaml template-http.yaml
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")  # offline expansion only needs a Region name

from samtranslator.parser.parser import Parser
from samtranslator.translator.transform import transform
from samtranslator.yaml_helper import yaml_parse


class NoManagedPolicies:
    """The templates use no managed policy names, so nothing has to be looked up in IAM."""

    def load(self):
        return {}


def expand(path):
    template = yaml_parse(Path(path).read_text())
    # sam deploy uploads app/ to S3 first; offline we put a placeholder S3 URI in its place.
    template["Globals"]["Function"]["CodeUri"] = "s3://placeholder-bucket/app.zip"
    return transform(template, {}, NoManagedPolicies(), Parser())


for path in sys.argv[1:]:
    resources = expand(path)["Resources"]
    print(f"== {path}: {len(resources)} resources")
    for name, res in sorted(resources.items(), key=lambda kv: kv[1]["Type"]):
        print(f"  {res['Type']:<40} {name}")
        props = res.get("Properties", {})
        if res["Type"] in ("AWS::ApiGatewayV2::Stage", "AWS::ApiGateway::Stage"):
            print(f"      stage={props.get('StageName')}  autoDeploy={props.get('AutoDeploy', False)}")
        if res["Type"] == "AWS::ApiGatewayV2::Api":
            body = props.get("Body", {})
            for route, ops in body.get("paths", {}).items():
                for verb, op in ops.items():
                    integ = op.get("x-amazon-apigateway-integration", {})
                    print(f"      route {verb.upper()} {route}  payloadFormatVersion={integ.get('payloadFormatVersion')}"
                          f"  security={[list(s)[0] for s in op.get('security', [])]}")
        if res["Type"] == "AWS::ApiGateway::RestApi":
            body = props.get("Body", {})
            for route, ops in body.get("paths", {}).items():
                for verb, op in ops.items():
                    integ = op.get("x-amazon-apigateway-integration", {})
                    print(f"      method {verb.upper()} {route}  integration={integ.get('type')}"
                          f"  validator={op.get('x-amazon-apigateway-request-validator')}"
                          f"  security={[list(s)[0] for s in op.get('security', [])]}")
