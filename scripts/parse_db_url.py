"""
Parseia DATABASE_URL e exporta variáveis individuais para GITHUB_ENV.
Usado pelo pipeline.yml para configurar dbt com host/user/pass separados.
"""
import os
import sys
import urllib.parse

url = os.environ.get("DATABASE_URL", "")
if not url:
    print("❌ DATABASE_URL não configurada — verifique os GitHub Secrets")
    sys.exit(1)

p = urllib.parse.urlparse(url)
qs = urllib.parse.parse_qs(p.query)
sslmode = qs.get("sslmode", ["require"])[0]

github_env = os.environ.get("GITHUB_ENV", "")
if github_env:
    with open(github_env, "a") as f:
        f.write(f"POSTGRES_HOST={p.hostname}\n")
        f.write(f"POSTGRES_PORT={p.port or 5432}\n")
        f.write(f"POSTGRES_DB={p.path.lstrip('/')}\n")
        f.write(f"POSTGRES_USER={p.username}\n")
        f.write(f"POSTGRES_PASSWORD={p.password}\n")
        f.write(f"POSTGRES_SSLMODE={sslmode}\n")
    print(f"✅ Variáveis configuradas: host={p.hostname} db={p.path.lstrip('/')}")
else:
    # Modo local: só imprime para debug
    print(f"host={p.hostname} port={p.port} db={p.path.lstrip('/')} user={p.username}")
