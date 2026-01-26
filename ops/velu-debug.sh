docker compose exec -T app sh -lc '
python - << "PY"
import os, inspect
from services.app_server.dependencies import scopes
from services.app_server import auth
print("ENV:", {k: os.getenv(k) for k in ["ENV","AUTH_MODE","TASK_DB_BACKEND","DATABASE_URL","VELU_API_KEY_PEPPER"]})
print("scopes:", scopes.__file__)
print(inspect.getsource(scopes))
print("auth:", auth.__file__)
print("hash pepper len:", len(os.getenv("VELU_API_KEY_PEPPER") or ""))
PY
'
