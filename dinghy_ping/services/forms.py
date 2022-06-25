from flask_wtf import FlaskForm
from wtforms import StringField, URLField, SubmitField, TextAreaField, IntegerField 
from wtforms.validators import DataRequired, Optional 

class HTTPCheckForm(FlaskForm):
    """
    Form for URL input and headers input
    """
    url = URLField('URL Check', validators=[DataRequired()])
    headers = TextAreaField('Optional Headers', render_kw={"placeholder": '{"Content-Type": "application/json"}'}, validators=[Optional()])
    submit = SubmitField('Ping')


class TCPCheckForm(FlaskForm):
    """
    Form for IP input and port input
    """
    tcp_endpoint = StringField('TCP Endpoint Check', validators=[DataRequired()], render_kw={"placeholder": "domain"})
    tcp_port = IntegerField('TCP Port', validators=[DataRequired()], render_kw={"placeholder": "3306"})
    submit = SubmitField('Ping')


class DNSCheckForm(FlaskForm):
    """
    Form for domain input
    """
    domain = StringField('Hostname', validators=[DataRequired()], render_kw={"placeholder": "domain"})
    nameserver = StringField('Optional Nameserver Override', validators=[Optional()], render_kw={"placeholder": "10.96.0.10"})
    submit = SubmitField('Ping')