"""Honor vhectorlab demo words, then larger sets for the thesis probe."""

from __future__ import annotations

# Exact DEMO_PAIRS from hbauzan/vhectorlab backend/vocab_merge.py
VHECTOR_HONOR: tuple[str, ...] = (
    "king",
    "rey",
    "queen",
    "reina",
    "man",
    "hombre",
    "woman",
    "mujer",
    "apple",
    "manzana",
    "computer",
    "computadora",
    "water",
    "agua",
    "peace",
    "paz",
    "dog",
    "perro",
    "cat",
    "gato",
)

# Words that exist in vhectorlab public/vocab.txt — honor the tool, then expand.
VOCAB_MECHANIC: tuple[str, ...] = (
    "engine",
    "brake",
    "tire",
    "oil",
    "spark",
    "piston",
    "clutch",
    "axle",
    "wrench",
    "coolant",
    "transmission",
    "radiator",
    "alternator",
    "thermostat",
    "suspension",
    "motor",
    "freno",
    "aceite",
    "bujia",
    "embrague",
)

VOCAB_IT: tuple[str, ...] = (
    "python",
    "javascript",
    "server",
    "database",
    "api",
    "compiler",
    "protocol",
    "kubernetes",
    "linux",
    "cache",
    "thread",
    "socket",
    "binary",
    "algorithm",
    "pointer",
    "servidor",
    "compilador",
    "protocolo",
    "hilo",
    "algoritmo",
)

VOCAB_NAMES: tuple[str, ...] = (
    "maria",
    "lucia",
    "ana",
    "carmen",
    "sofia",
    "elena",
    "isabel",
    "laura",
    "valentina",
    "camila",
    "julia",
    "clara",
    "rosa",
    "patricia",
    "andrea",
    "monica",
    "daniela",
    "florencia",
    "martina",
    "agustina",
)

_VEHICLES = (
    "Chevrolet Prisma",
    "sedan",
    "hatchback",
    "pickup",
    "utilitario",
    "camioneta",
)
_PARTS = (
    "eje trasero",
    "pastillas de freno",
    "bujia de iridio",
    "bomba de agua",
    "filtro de habitaculo",
    "caja automatica",
    "radiador",
    "alternador",
    "tensor de correa",
    "amortiguador",
)
_IT_THINGS = (
    "indice B-tree",
    "lock pessimista",
    "cola Kafka",
    "pod de Kubernetes",
    "socket TCP",
    "cache LRU",
    "garbage collector",
    "syscall mmap",
    "handshake TLS",
    "WAL de Postgres",
)
_CRYPTO_BITS = (
    "AES-GCM",
    "HKDF-SHA256",
    "curva P-256",
    "Kyber768",
    "HMAC-SHA256",
    "ChaCha20-Poly1305",
    "RSA-OAEP",
    "X25519",
)
_LLM_BITS = (
    "atencion multi-cabeza",
    "residual stream",
    "cross-entropy",
    "RoPE",
    "KV cache",
    "temperatura 0",
    "capa de normalizacion RMSNorm",
    "logits pre-softmax",
)


def honor_tokens() -> list[tuple[str, str]]:
    return [("honor", w) for w in VHECTOR_HONOR]


def token_rows() -> list[tuple[str, str]]:
    rows = honor_tokens()
    rows.extend(("mechanic_token", w) for w in VOCAB_MECHANIC)
    rows.extend(("it_token", w) for w in VOCAB_IT)
    rows.extend(("names_token", w) for w in VOCAB_NAMES)
    return rows


def _mechanic_chunk(i: int) -> str:
    vehicle = _VEHICLES[i % len(_VEHICLES)]
    part = _PARTS[i % len(_PARTS)]
    psi = 28 + (i % 12)
    nm = 18 + (i % 40)
    km = 5000 + (i % 20) * 1000
    return (
        f"Manual de taller {vehicle}. La presion en frio del {part} se verifica "
        f"antes de un viaje largo: especificación {psi} PSI. El torque de la "
        f"tuerca correspondiente es {nm} Nm. Cambiar aceite y filtro cada {km} km "
        f"bajo servicio severo. No mezclar refrigerante. Si hay chirrido de freno, "
        f"inspeccionar pastillas y liquido DOT. El diagnostico OBD no reemplaza "
        f"la medicion mecanica del holgura de valvula ni el estado del termostato."
    )


def _it_chunk(i: int) -> str:
    thing = _IT_THINGS[i % len(_IT_THINGS)]
    port = 1024 + (i % 4000)
    n = 2 + (i % 16)
    return (
        f"Nota de operaciones. El {thing} se configura con {n} replicas. "
        f"El servicio escucha el puerto {port}. Un timeout de 30s en el handshake "
        f"deja la transaccion en estado indeterminado: hay que idempotenciar el "
        f"cliente. El profiler muestra contencion en el lock; no es latencia de red. "
        f"Logs en JSON, metricas por request_id, y un circuit breaker antes de "
        f"reintentar. Python y el servidor no son el mismo runtime si cada uno "
        f"abre su propia conexion a la base."
    )


def _name_chunk(i: int) -> str:
    name = VOCAB_NAMES[i % len(VOCAB_NAMES)]
    other = VOCAB_NAMES[(i + 3) % len(VOCAB_NAMES)]
    year = 1978 + (i % 30)
    return (
        f"{name.capitalize()} nacio en {year}. En la reunion familiar, "
        f"{other.capitalize()} trajo fotos de la infancia. Hablaron de la abuela, "
        f"del nombre de pila, de como se pronuncia en cada casa. No hay torque, "
        f"ni API, ni cipher: solo el nombre, el apodo y quien vino a merendar."
    )


def _crypto_science(i: int) -> str:
    prim = _CRYPTO_BITS[i % len(_CRYPTO_BITS)]
    nist = 128 + (i % 4) * 64
    return (
        f"Construccion criptografica. {prim} se usa aqui como AEAD: el nonce de "
        f"{12 + (i % 4)} bytes no se reutiliza. La clave se deriva con HKDF sobre "
        f"un secreto de {nist} bits. El tag autentica ciphertext y AAD. Un nonce "
        f"repetido rompe confidencialidad. La reduccion de seguridad asume el "
        f"modelo estandar; no hay oraculo de cifrado elegido mas alla del bound "
        f"de queries. Los floats del embedder no son el PRF. Verificar constantes "
        f"NIST y el orden de concatenacion salt || ikm || info."
    )


def _llm_science(i: int) -> str:
    bit = _LLM_BITS[i % len(_LLM_BITS)]
    d = 256 * (1 + (i % 8))
    return (
        f"Nota de arquitectura de un transformador. La {bit} opera en dimension "
        f"{d}. La atencion es softmax(QK^T / sqrt(d_k)) V. El residual stream "
        f"acumula lecturas y escrituras de cada capa. Un cambio de 1e-3 en un "
        f"logit no es una unidad comparable entre cabezas si las varianzas de "
        f"eje difieren. La evidencia de membresia de un prompt no es el % PASS "
        f"de un clasificador de dano; es la geometria del vector denso."
    )


def _poetry(i: int) -> str:
    name = VOCAB_NAMES[i % len(VOCAB_NAMES)]
    return (
        f"En el umbral de un siglo de vidrio, {name.capitalize()} abrio una rosa "
        f"hecha de relampagos. Los dragones no calculan nonces: beben luna y "
        f"escupen constelaciones. Cada suspiro era un oceano, cada mirada un "
        f"hechizo que doblaba los relojes. Exagero: el viento firmo un pacto "
        f"con las campanas y el tiempo se arrodillo. No hay taller ni cluster. "
        f"Solo magia espesa, perfume de mito y una corona que no es un rey."
    )


def _crypto_poetic(i: int) -> str:
    prim = _CRYPTO_BITS[i % len(_CRYPTO_BITS)]
    return (
        f"Canto al {prim}: la llave duerme en una boveda de luna, el nonce es "
        f"un relampago que no debe repetirse, el tag es un sello de cera sobre "
        f"el mensaje. Digo lo mismo que el paper, pero con dragones: si el "
        f"relampago cae dos veces, el secreto se derrama. No invento otro "
        f"algoritmo; disfrazo el mismo."
    )


def chunk_rows(n_per_family: int) -> list[tuple[str, str]]:
    n = max(1, n_per_family)
    rows: list[tuple[str, str]] = []
    for i in range(n):
        rows.append(("mechanic_chunk", _mechanic_chunk(i)))
        rows.append(("it_chunk", _it_chunk(i)))
        rows.append(("names_chunk", _name_chunk(i)))
        rows.append(("crypto_science", _crypto_science(i)))
        rows.append(("llm_science", _llm_science(i)))
        rows.append(("poetry", _poetry(i)))
        rows.append(("crypto_poetic", _crypto_poetic(i)))
    return rows
