"""The payload ``info()`` answers, shaped as a Flow PT 8.91 site sends it (api3 046)."""

DEFAULT_INFO = {
    "analytics_site_id": "mockgun",
    "analytics_site_name": "mockgun",
    "api_max_entities_per_page": 5000,
    "authentication_app_session_launcher_enabled": True,
    "full_version": [8, 91, 0, 0],
    "s3_direct_uploads_enabled": True,
    "s3_enabled_upload_types": {"*": ["*"]},
    "s3_uploads_enabled": True,
    "shotgunlocalhost_browser_integration_enabled": True,
    "unified_login_flow_enabled": True,
    "user_authentication_method": "oxygen",
    "version": [8, 91, 0],
}
