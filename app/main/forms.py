from flask_wtf import FlaskForm
from wtforms import (
    IntegerField, StringField, SubmitField,
    TextAreaField, URLField, SelectField
)
from flask_wtf.file import FileField, FileRequired, FileAllowed

from wtforms.validators import DataRequired, Optional, FileRequired, FileAllowed


class HTTPCheckForm(FlaskForm):
    """
    Form for URL input and headers input
    """

    url = URLField("URL Check", validators=[DataRequired()])
    headers = TextAreaField(
        "Optional Headers",
        render_kw={"placeholder": '{"Content-Type": "application/json"}'},
        validators=[Optional()],
    )
    submit = SubmitField("Ping")


class TCPCheckForm(FlaskForm):
    """
    Form for IP input and port input
    """

    tcp_endpoint = StringField(
        "TCP Endpoint Check",
        validators=[DataRequired()],
        render_kw={"placeholder": "domain"},
    )
    tcp_port = IntegerField(
        "TCP Port", validators=[DataRequired()], render_kw={"placeholder": "3306"}
    )
    submit = SubmitField("Ping")


class DNSCheckForm(FlaskForm):
    """
    Form for domain input
    """

    domain = StringField(
        "Hostname", validators=[DataRequired()], render_kw={"placeholder": "domain"}
    )
    nameserver = StringField(
        "Optional Nameserver Override",
        validators=[Optional()],
        render_kw={"placeholder": "10.96.0.10"},
    )
    submit = SubmitField("Ping")


class GrpCurlForm(FlaskForm):
    """
    Form for grpcurl
    """

    grpc_endpoint = SelectField(
        "Grpcurl Endpoint Select",
        validators=[DataRequired()],
        # lookup choices from redis
    )
    
    grpc_method = StringField(
        "Grpcurl Method",
        validators=[DataRequired()],
        render_kw={"placeholder": "method"},
    )

    json_file_upload = FileField(
        "JSON File Upload. The file must be in JSON format, and can contain multiple JSON objects.",
        validators=[FileRequired(), FileAllowed(["json"], "JSON only!")],
    )

    submit = SubmitField("Grpcurl")


class GrpcEndpointForm(FlaskForm):
    """
    Form for grpcurl endpoint submission into available endpoints
    """

    grpc_endpoint = StringField(
        "Grpcurl Service Endpoint",
        validators=[DataRequired()],
        render_kw={"placeholder": "domain"},
    )

    grpc_port = IntegerField(
        "Grpcurl Port", validators=[DataRequired()], render_kw={"placeholder": "9090"}
    )

    grpc_protocol_git_repo = StringField(
        "Grpcurl Protocol Git Repo",
        validators=[DataRequired()],
        render_kw={"placeholder": "https://<git_repo_url>.git"},
    )

    submit = SubmitField("Grpcurl Endpoint")
