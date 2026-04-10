import os
import logging

# Configuración del bot
TOKEN = "8617963508:AAHU4Bh6yy2gJkmTQWPA055FzxwSxBqc1j4"

# Cookies de YouTube
COOKIES = """# Netscape HTTP Cookie File
# http://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file!  Do not edit.

.youtube.com	TRUE	/	TRUE	1810257985	PREF	tz=Etc.GMT%2B8
.youtube.com	TRUE	/	FALSE	1809461326	HSID	AtfotEu-QMxl66B3R
.youtube.com	TRUE	/	TRUE	1809461326	SSID	AygDdvIzDsspiUtMX
.youtube.com	TRUE	/	FALSE	1809461326	APISID	FqaV7eSo7nZpaC1O/AOwgwT-5qfdMEq4lU
.youtube.com	TRUE	/	TRUE	1809461326	SAPISID	Ah9J56HlMn38eqrH/AC_7hrl1QIfdLzjmx
.youtube.com	TRUE	/	TRUE	1809461326	__Secure-1PAPISID	Ah9J56HlMn38eqrH/AC_7hrl1QIfdLzjmx
.youtube.com	TRUE	/	TRUE	1809461326	__Secure-3PAPISID	Ah9J56HlMn38eqrH/AC_7hrl1QIfdLzjmx
.youtube.com	TRUE	/	FALSE	1809461326	SID	g.a0008QgBLlJjTK4BOQxslA5e--9SkQK0U1M9fUbK1VsdCcRoZ0zkyszwIctIWO-d-0uyydHRYQACgYKAaUSARASFQHGX2MicHgDOM4SSoPE-ShshVaPTxoVAUF8yKqxKpV2CaiU88jnp2lb1MQJ0076
.youtube.com	TRUE	/	TRUE	1809461326	__Secure-1PSID	g.a0008QgBLlJjTK4BOQxslA5e--9SkQK0U1M9fUbK1VsdCcRoZ0zki0dwnNS-FrJcpbSufDeC5gACgYKAYcSARASFQHGX2MiJAiLjx3jp52ToMUb0zc7tBoVAUF8yKo8P471ptdLz8aGDmeVkxEm0076
.youtube.com	TRUE	/	TRUE	1809461326	__Secure-3PSID	g.a0008QgBLlJjTK4BOQxslA5e--9SkQK0U1M9fUbK1VsdCcRoZ0zkb0hlf2UOBuijeaHGAqrX9wACgYKAW4SARASFQHGX2Mi5g-RbFVzT8C7FB2P9alNOBoVAUF8yKo7ZKcFyMmbu79m3BSFkEGW0076
.youtube.com	TRUE	/	TRUE	1809461329	LOGIN_INFO	AFmmF2swRAIge_GlgcN5oDe_emGfzk7MvAWoYMRhUAkZAJ26QnfSijoCIGJuQR5HiVRVq_30dwwvQ1veAyANh2uyRM7G6_Am-FGQ:QUQ3MjNmd212dXZaN2dnTHI2a1A1UG5pNzJvQXpjRVFrVG9adWtTOVRRRGJWZEl4UE1USG80SDJMZXdnUjlKUENhSTVudVBOWWlCM2FsUHZKS1pwYnlsS0JNSnVqMXdBc0RmU0pnZHlheE1WOHByX3VwMnJiMHVBbUQ4c09OamhsSU1vNTJSd0hkMEhwQ2FZOFVtXzJJRkwtMHY4Tmx0QlFB
.youtube.com	TRUE	/	TRUE	1791181477	__Secure-BUCKET	CIUC
.youtube.com	TRUE	/	TRUE	1807233988	__Secure-1PSIDTS	sidts-CjUBWhotCcL_GMj-cV9d076mjb6AjoCcFyowLylaW6yCgWxbwXImYCa8ocV-JDKBcP6uZXB6vxAA
.youtube.com	TRUE	/	TRUE	1807233988	__Secure-3PSIDTS	sidts-CjUBWhotCcL_GMj-cV9d076mjb6AjoCcFyowLylaW6yCgWxbwXImYCa8ocV-JDKBcP6uZXB6vxAA
.youtube.com	TRUE	/	FALSE	1807233990	SIDCC	AKEyXzXLxx4_W_QISvPSValvSBbxYeh5oRnNTZFDMpDXcM0zkwMokDxKsP6Rcm2y4HO5FqH7Mg
.youtube.com	TRUE	/	TRUE	1807233990	__Secure-1PSIDCC	AKEyXzVOcP1iQaXDE0PAhWv9jvbJi0SjpGGrW5O_r-g54H2MnCJ-vMW4rdVebXjIjr5aEKinwA
.youtube.com	TRUE	/	TRUE	1807233990	__Secure-3PSIDCC	AKEyXzW9cb3gt4dF5CroHW6YeXbSFAC8dZ4oiLmYC-6a99G5WQzzg2nVvJdqniCQKOVnczrdjw
"""

VERSION = "0.5.0"

# Configuración de descargas
DOWNLOAD_DIR = "downloads"
SUSCRIPCIONES_FILE = "subscripciones.json"

# Límite por defecto
limite = 10

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)