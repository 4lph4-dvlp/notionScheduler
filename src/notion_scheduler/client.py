"""Direct Notion API transport for Scheduler tasks."""


class NotionClient:
    """Configured Notion transport."""

    def __init__(self, *, token="", database_id="", database_name="", sdk=None, **kwargs):
        self.token = token
        self.database_id = database_id
        self.database_name = database_name
        self.sdk = sdk

    def resolve_target(self):
        return None

    def validate_scheduler_schema(self, data_source_id):
        return None

    def query_pages(self, data_source_id):
        return []
