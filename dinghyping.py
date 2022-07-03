from app import create_app
from app.models.dinghy_data import DinghyData
from app.models.dinghy_dns import DinghyDNS

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {"DinghyDNS": DinghyDNS, "DinghyData": DinghyData}
