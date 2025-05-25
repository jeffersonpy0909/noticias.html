import feedparser
import requests
from bs4 import BeautifulSoup
import random
from datetime import datetime
from urllib.parse import quote
import time
import yfinance as yf
import threading
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuración de archivos
ARCHIVO_SUSCRIPTORES = "suscriptores.json"  # Archivo para almacenar los suscriptores
CONFIG_EMAIL = {
    "servidor": "smtp.gmail.com",          # Servidor SMTP para enviar emails
    "puerto": 587,                         # Puerto del servidor SMTP
    "usuario": "tucorreo@gmail.com",       # Email desde el que se enviarán notificaciones
    "password": "tucontraseña"             # Contraseña del email
}
ARCHIVO_DATOS = "noticias.json"            # Archivo para almacenar los datos de noticias
RUTA_HTML = "noticias.html"                # Ruta donde se generará el archivo HTML

# Configuración de categorías
CATEGORIAS = [
    "Tecnología", "Recetas de comida", "Noticias", "Ciencia",
    "Programación", "Gadgets", "Inteligencia Artificial", "Empleos"
]

# Configuración ampliada de fuentes por categoría
FUENTES_RSS = {
    "Tecnología": [
        {"url": "https://feeds.feedburner.com/muycomputer", "nombre": "MuyComputer"},
        {"url": "https://www.xataka.com/rss", "nombre": "Xataka"},
        {"url": "https://www.genbeta.com/feed", "nombre": "Genbeta"},
        {"url": "https://hipertextual.com/feed", "nombre": "Hipertextual"},
        {"url": "https://www.androidsis.com/feed/", "nombre": "Androidsis"},
        {"url": "https://feeds.weblogssl.com/xataka2", "nombre": "Xataka Móvil"},
        {"url": "https://wwwhatsnew.com/feed/", "nombre": "WWWhatsnew"},
        {"url": "https://www.applesfera.com/index.xml", "nombre": "Applesfera"},
        {"url": "https://elandroidelibre.elespanol.com/feed", "nombre": "El Androide Libre"},
        {"url": "https://omicrono.elespanol.com/feed/", "nombre": "Omicrono"}
    ],
    "Programación": [
        {"url": "https://www.smashingmagazine.com/feed/", "nombre": "Smashing Magazine"},
        {"url": "https://css-tricks.com/feed/", "nombre": "CSS-Tricks"},
        {"url": "https://dev.to/feed", "nombre": "DEV Community"},
        {"url": "https://stackoverflow.blog/feed/", "nombre": "Stack Overflow Blog"},
        {"url": "https://martinfowler.com/feed.atom", "nombre": "Martin Fowler"}
    ],
    "Inteligencia Artificial": [
        {"url": "https://openai.com/blog/rss/", "nombre": "OpenAI Blog"},
        {"url": "https://deepmind.com/blog/feed.xml", "nombre": "DeepMind Blog"},
        {"url": "https://ai.googleblog.com/feeds/posts/default", "nombre": "Google AI Blog"},
        {"url": "https://blog.tensorflow.org/feeds/posts/default", "nombre": "TensorFlow Blog"}
    ],
    "Recetas de comida": [
        {"url": "https://www.directoalpaladar.com/feed", "nombre": "Directo al Paladar"},
        {"url": "https://www.recetasderechupete.com/feed/", "nombre": "Recetas de Rechupete"},
        {"url": "https://www.pequerecetas.com/feed/", "nombre": "PequeRecetas"},
        {"url": "https://www.cocinafacil.com.mx/feed/", "nombre": "Cocina Fácil"}
    ],
    "Noticias": [
        {"url": "https://news.google.com/rss?hl=es-419&gl=US&ceid=US:es-419", "nombre": "Google News"},
        {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "nombre": "NY Times"},
        {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "nombre": "BBC Mundo"}
    ],
    "Ciencia": [
        {"url": "https://www.nationalgeographic.com.es/rss/temas/ciencia", "nombre": "National Geographic Ciencia"},
        {"url": "https://www.investigacionyciencia.es/rss/noticias", "nombre": "Investigación y Ciencia"},
        {"url": "https://www.scientificamerican.com/rss/", "nombre": "Scientific American"}
    ],
    "Gadgets": [
        {"url": "https://www.theverge.com/rss/index.xml", "nombre": "The Verge"},
        {"url": "https://www.engadget.com/rss.xml", "nombre": "Engadget"},
        {"url": "https://www.cnet.com/rss/news/", "nombre": "CNET"},
        {"url": "https://www.wired.com/feed/rss", "nombre": "Wired"}
    ],
    "Empleos": [
        {"url": "https://www.chiripas.com", "nombre": "chiripas - Desarrollador"},
      
    ]
}

def cargar_suscriptores():
    """Carga la lista de suscriptores desde el archivo"""
    try:
        with open(ARCHIVO_SUSCRIPTORES, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"suscriptores": []}

def guardar_suscriptores(suscriptores):
    """Guarda la lista de suscriptores en el archivo"""
    with open(ARCHIVO_SUSCRIPTORES, 'w', encoding='utf-8') as f:
        json.dump(suscriptores, f, ensure_ascii=False, indent=2)

def enviar_notificacion(destinatario, asunto, mensaje):
    """Envía una notificación por email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = CONFIG_EMAIL["usuario"]
        msg['To'] = destinatario
        msg['Subject'] = asunto
        
        msg.attach(MIMEText(mensaje, 'plain'))
        
        server = smtplib.SMTP(CONFIG_EMAIL["servidor"], CONFIG_EMAIL["puerto"])
        server.starttls()
        server.login(CONFIG_EMAIL["usuario"], CONFIG_EMAIL["password"])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error al enviar email: {str(e)}")
        return False

def extraer_imagenes(url):
    """Extrae imágenes de la página original con sus dimensiones"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        imagenes = []
        
        # Patrones comunes para imágenes destacadas
        patrones = [
            {'tag': 'img', 'class_': 'featured-image'},
            {'tag': 'img', 'itemprop': 'image'},
            {'tag': 'img', 'class_': 'wp-post-image'},
            {'tag': 'img', 'loading': 'lazy'},
            {'tag': 'meta', 'property': 'og:image'},
            {'tag': 'link', 'rel': 'image_src'}
        ]
        
        for patron in patrones:
            if patron['tag'] == 'meta' and patron.get('property') == 'og:image':
                for meta in soup.find_all('meta', property='og:image'):
                    imagenes.append({
                        'url': meta.get('content'),
                        'width': 'auto',
                        'height': 'auto'
                    })
            elif patron['tag'] == 'link' and patron.get('rel') == 'image_src':
                for link in soup.find_all('link', rel='image_src'):
                    imagenes.append({
                        'url': link.get('href'),
                        'width': 'auto',
                        'height': 'auto'
                    })
            else:
                for img in soup.find_all(patron['tag'], class_=patron.get('class_'), 
                                   itemprop=patron.get('itemprop'), 
                                   loading=patron.get('loading')):
                    src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                    if src and src.startswith(('http://', 'https://')):
                        width = img.get('width', 'auto')
                        height = img.get('height', 'auto')
                        imagenes.append({
                            'url': src,
                            'width': width,
                            'height': height
                        })
        
        # Eliminar duplicados
        seen = set()
        imagenes_unicas = []
        for img in imagenes:
            if img['url'] not in seen:
                seen.add(img['url'])
                imagenes_unicas.append(img)
        
        return imagenes_unicas[:5] if imagenes_unicas else None
    
    except Exception as e:
        print(f"Error al extraer imágenes: {str(e)}")
        return None

def obtener_imagen_relacionada(query, url):
    # Primero intentar extraer imágenes de la página original
    imagenes = extraer_imagenes(url)
    if imagenes:
        # Seleccionar la imagen con mejor relación de aspecto
        imagenes_validas = [img for img in imagenes if img['url'] and img['url'].startswith(('http://', 'https://'))]
        if imagenes_validas:
            try:
                mejor_imagen = max(imagenes_validas, 
                                 key=lambda x: (int(x['width']) if x['width'].isdigit() else 0, 
                                               int(x['height']) if x['height'].isdigit() else 0))
                return mejor_imagen['url']
            except:
                return imagenes_validas[0]['url']
    
    # Si no hay imágenes en la página, usar placeholder
    colors = ["FF5733", "33FF57", "3357FF", "F3FF33", "FF33F3"]
    color = random.choice(colors)
    return f"https://via.placeholder.com/1200x630/{color}/FFFFFF?text={quote(query)}"

def extraer_contenido_completo(soup, categoria):
    """Extrae contenido completo estructurado de la página"""
    contenido = ""
    
    # Extraer el artículo principal
    article = soup.find('article') or soup.find('div', class_=lambda x: x and 'article' in x.lower())
    
    if article:
        # Eliminar elementos no deseados dentro del artículo
        for element in article(['script', 'style', 'nav', 'footer', 'iframe', 'aside', 'figure']):
            element.decompose()
        
        # Extraer párrafos y encabezados
        elementos = article.find_all(['p', 'h2', 'h3', 'h4', 'ul', 'ol'])
        for elem in elementos:
            if elem.name in ['h2', 'h3', 'h4']:
                contenido += f"\n\n{elem.get_text().strip()}\n{'=' if elem.name == 'h2' else '-' * len(elem.get_text().strip())}\n"
            elif elem.name == 'ul':
                contenido += "\n" + "\n".join([f"• {li.get_text().strip()}" for li in elem.find_all('li')]) + "\n"
            elif elem.name == 'ol':
                contenido += "\n" + "\n".join([f"{i+1}. {li.get_text().strip()}" for i, li in enumerate(elem.find_all('li'))]) + "\n"
            else:
                contenido += f"\n{elem.get_text().strip()}\n"
    
    return contenido.strip() if contenido else "Contenido no disponible."

def extraer_ingredientes(soup):
    """Función especializada para extraer ingredientes de recetas"""
    ingredientes = []
    
    patrones = [
        {'tag': 'div', 'class_': 'ingredientes'},
        {'tag': 'ul', 'class_': 'ingredients'},
        {'tag': 'div', 'class_': 'ingredients'},
        {'tag': 'section', 'class_': 'ingredientes'},
        {'tag': 'div', 'itemprop': 'recipeIngredient'}
    ]
    
    for patron in patrones:
        elementos = soup.find_all(patron['tag'], class_=patron.get('class_'), itemprop=patron.get('itemprop'))
        for elemento in elementos:
            items = elemento.find_all('li')
            if not items:
                texto = elemento.get_text(' ', strip=True)
                if texto:
                    ingredientes.append(texto)
            else:
                for item in items:
                    texto = item.get_text(' ', strip=True)
                    if texto:
                        ingredientes.append(texto)
    
    if not ingredientes:
        listas = soup.find_all(['ul', 'ol'])
        for lista in listas:
            texto_lista = lista.get_text(' ', strip=True).lower()
            if 'ingrediente' in texto_lista:
                items = lista.find_all('li')
                for item in items:
                    texto = item.get_text(' ', strip=True)
                    if texto:
                        ingredientes.append(texto)
    
    return ingredientes if ingredientes else None

def obtener_contenido(url, categoria):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.content, 'html.parser')

        # Eliminar elementos no deseados
        for element in soup(['script', 'style', 'nav', 'footer', 'iframe', 'aside']):
            element.decompose()
        
        if categoria == "Recetas de comida":
            ingredientes = extraer_ingredientes(soup)
            if ingredientes:
                contenido_ingredientes = "🍴 Ingredientes:\n\n" + "\n".join(f"• {ing}" for ing in ingredientes)
                
                preparacion = []
                patrones_prep = [
                    {'tag': 'div', 'class_': 'preparacion'},
                    {'tag': 'ol', 'class_': 'steps'},
                    {'tag': 'div', 'class_': 'instructions'},
                    {'tag': 'div', 'itemprop': 'recipeInstructions'}
                ]
                
                for patron in patrones_prep:
                    elementos = soup.find_all(patron['tag'], class_=patron.get('class_'), itemprop=patron.get('itemprop'))
                    for elemento in elementos:
                        pasos = elemento.find_all('li') or elemento.find_all('p')
                        for i, paso in enumerate(pasos, 1):
                            texto = paso.get_text(' ', strip=True)
                            if texto:
                                preparacion.append(f"{i}. {texto}")
                
                contenido_preparacion = "\n\n👩‍🍳 Preparación:\n\n" + "\n".join(preparacion) if preparacion else ""
                
                return contenido_ingredientes + contenido_preparacion
        
        # Para otras categorías, extraer contenido estructurado
        contenido = extraer_contenido_completo(soup, categoria)
        
        return contenido if contenido else "Contenido no disponible."
    
    except Exception as e:
        print(f"❌ Error al obtener contenido de {url}: {str(e)}")
        return "Contenido no disponible."

def obtener_info_bolsa():
    print("📈 Obteniendo datos de bolsa en tiempo real...")
    indices = {
        "S&P 500": {"symbol": "^GSPC", "emoji": "📊"},
        "NASDAQ": {"symbol": "^IXIC", "emoji": "💻"},
        "DOW JONES": {"symbol": "^DJI", "emoji": "🏭"},
        "IBEX 35": {"symbol": "^IBEX", "emoji": "🇪🇸"},
        "BITCOIN": {"symbol": "BTC-USD", "emoji": "₿"},
        "ETHEREUM": {"symbol": "ETH-USD", "emoji": "Ξ"}
    }

    info = []
    for nombre, data in indices.items():
        try:
            ticker = yf.Ticker(data['symbol'])
            hist = ticker.history(period="1d", interval="1m")
            
            if not hist.empty:
                ultimo = hist['Close'].iloc[-1]
                anterior = hist['Close'].iloc[0] if len(hist) > 1 else ultimo
                cambio = ultimo - anterior
                cambio_porcentual = (cambio / anterior) * 100
                
                clase = "positivo" if cambio >= 0 else "negativo"
                signo = "+" if cambio >= 0 else ""
                
                if "BTC" in data['symbol'] or "ETH" in data['symbol']:
                    info_item = f"{data['emoji']} {nombre}: ${ultimo:,.2f} ({signo}{cambio:,.2f} | {signo}{cambio_porcentual:.2f}%)"
                else:
                    info_item = f"{data['emoji']} {nombre}: {ultimo:,.2f} pts ({signo}{cambio:,.2f} | {signo}{cambio_porcentual:.2f}%)"
                
                info.append((info_item, clase))
            else:
                info.append((f"{data['emoji']} {nombre}: Datos no disponibles", ""))
            
            time.sleep(1)
        except Exception as e:
            print(f"Error al obtener datos de {nombre}: {str(e)}")
            info.append((f"{data['emoji']} {nombre}: Error", ""))

    try:
        sp500 = yf.Ticker("^GSPC")
        hist = sp500.history(period="5d")
        if len(hist) >= 2:
            cambio_5d = (hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100
            tendencia = "alcista" if cambio_5d > 0.5 else "bajista" if cambio_5d < -0.5 else "lateral"
            emoji = "📈" if tendencia == "alcista" else "📉" if tendencia == "bajista" else "↔️"
            info.append((f"{emoji} Tendencia: {tendencia} (S&P 500 {cambio_5d:+.2f}% 5d)", ""))
    except Exception as e:
        print(f"Error al obtener tendencia: {str(e)}")

    return info

def buscar_noticia_por_categoria(categoria):
    print(f"\n🔍 Buscando contenido en categoría: {categoria}")
    
    if categoria not in FUENTES_RSS:
        print(f"No hay fuentes configuradas para {categoria}")
        return None
    
    noticias = []
    for fuente in FUENTES_RSS[categoria]:
        try:
            feed = feedparser.parse(fuente['url'])
            for entry in feed.entries[:10]:  # Aumentamos a 10 entradas por fuente
                try:
                    # Extraer imágenes antes de agregar la noticia
                    imagenes = extraer_imagenes(entry.link) or []
                    
                    noticias.append({
                        "titulo": entry.title,
                        "url": entry.link,
                        "fuente": fuente['nombre'],
                        "fecha": entry.get('published', 'Fecha no disponible'),
                        "categoria": categoria,
                        "descripcion": entry.get('description', ''),
                        "imagenes": [img['url'] for img in imagenes[:3]] if imagenes else []
                    })
                except Exception as e:
                    print(f"  ⚠️ Error procesando contenido: {str(e)}")
        except Exception as e:
            print(f"❌ Error con fuente {fuente['nombre']}: {str(e)}")
    
    if not noticias:
        print(f"No se encontraron contenidos en {categoria}")
        return None
    
    return noticias

def buscar_noticia_en_otras_categorias(categoria_original):
    """Busca noticias en otras categorías si la original no tiene contenido"""
    categorias_disponibles = list(FUENTES_RSS.keys())
    
    # Eliminar la categoría original de la lista
    if categoria_original in categorias_disponibles:
        categorias_disponibles.remove(categoria_original)
    
    # Buscar en otras categorías aleatoriamente
    random.shuffle(categorias_disponibles)
    
    for categoria in categorias_disponibles:
        noticias = buscar_noticia_por_categoria(categoria)
        if noticias:
            print(f"✅ Se encontraron noticias en la categoría {categoria} como alternativa")
            return noticias[:5]  # Devolver hasta 5 noticias de la categoría alternativa
    
    print("⚠️ No se encontraron noticias en ninguna categoría alternativa")
    return None

def cargar_datos():
    """Carga los datos existentes del archivo JSON"""
    try:
        with open(ARCHIVO_DATOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"noticias": {}, "ultima_actualizacion": None}

def guardar_datos(datos):
    """Guarda los datos en el archivo JSON"""
    with open(ARCHIVO_DATOS, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def actualizar_noticias():
    """Actualiza todas las noticias de todas las categorías"""
    datos = cargar_datos()
    datos["noticias"] = {}
    
    for categoria in FUENTES_RSS.keys():
        noticias = buscar_noticia_por_categoria(categoria)
        
        # Si no hay noticias en esta categoría, buscar en otras
        if not noticias:
            noticias = buscar_noticia_en_otras_categorias(categoria)
        
        if noticias:
            datos["noticias"][categoria] = noticias
    
    datos["ultima_actualizacion"] = datetime.now().isoformat()
    guardar_datos(datos)
    
    # Enviar notificaciones a suscriptores si hay nuevas noticias
    enviar_notificaciones_suscriptores(datos)
    
    return datos

def enviar_notificaciones_suscriptores(datos):
    """Envía notificaciones por email a los suscriptores"""
    suscriptores = cargar_suscriptores()
    
    if not suscriptores.get("suscriptores"):
        return
    
    # Preparar el resumen de noticias
    asunto = f"📰 Resumen de noticias - {datetime.now().strftime('%d/%m/%Y')}"
    mensaje = "¡Estas son las noticias destacadas de hoy!\n\n"
    
    for categoria, noticias in datos["noticias"].items():
        mensaje += f"=== {categoria.upper()} ===\n"
        for i, noticia in enumerate(noticias[:3], 1):  # Máximo 3 por categoría
            mensaje += f"{i}. {noticia['titulo']} - {noticia['fuente']}\n"
            mensaje += f"   Leer más: {noticia['url']}\n\n"
    
    mensaje += "\nPara dejar de recibir estas notificaciones, visita nuestro sitio web."
    
    # Enviar a cada suscriptor
    for suscriptor in suscriptores["suscriptores"]:
        enviar_notificacion(suscriptor, asunto, mensaje)

def generar_html(datos):
    """Genera la página HTML completa con todas las categorías"""
    info_bolsa = obtener_info_bolsa()
    ticker_items = "".join(f'<span class="ticker-item {clase}">{item}</span>\n' for item, clase in info_bolsa)
    
    # Generar HTML para cada categoría
    categorias_html = []
    noticias_html = []
    
    for categoria, items in datos["noticias"].items():
        # HTML para el selector de categorías
        categoria_id = categoria.lower().replace(" ", "-").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        categorias_html.append(f'<a href="#{categoria_id}" class="categoria-item">{categoria}</a>')
        
        # HTML para las noticias de cada categoría
        categoria_noticias = []
        for i, noticia in enumerate(items[:5]):  # Mostrar hasta 5 noticias por categoría
            imagen_principal = noticia["imagenes"][0] if noticia["imagenes"] else obtener_imagen_relacionada(noticia["titulo"], noticia["url"])
            
            # Galería de imágenes adicionales
            galeria_html = ""
            if len(noticia["imagenes"]) > 1:
                galeria_html = '<div class="galeria">' + \
                              "".join(f'<img src="{img}" alt="Imagen {i+1}" loading="lazy">' 
                                     for i, img in enumerate(noticia["imagenes"][1:4])) + \
                              '</div>'
            
            categoria_noticias.append(f"""
            <article class="noticia">
                <h3 class="noticia-titulo">{noticia["titulo"]}</h3>
                <div class="noticia-meta">
                    <span class="noticia-fuente">{noticia["fuente"]}</span>
                    <span class="noticia-fecha">{noticia["fecha"]}</span>
                </div>
                <img src="{imagen_principal}" alt="{noticia["titulo"]}" class="noticia-imagen">
                {galeria_html}
                <div class="noticia-descripcion">{noticia["descripcion"]}</div>
                <a href="{noticia["url"]}" class="noticia-enlace" target="_blank">Leer más</a>
            </article>
            """)
        
        noticias_html.append(f"""
        <section id="{categoria_id}" class="categoria-seccion">
            <h2 class="categoria-titulo">{categoria}</h2>
            <div class="noticias-container">
                {"".join(categoria_noticias)}
            </div>
        </section>
        """)
    
    # CSS completo
    css = """
    <style>
    :root {
      --primary-color: #003366;
      --secondary-color: #e63946;
      --accent-color: #457b9d;
      --light-color: #f1faee;
      --dark-color: #1d3557;
      --food-color: #ff9e80;
    }

    body {
      font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      margin: 0;
      background: #f8f9fa;
      line-height: 1.6;
      color: #333;
    }

    .navbar {
      background: white;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 1000;
    }

    .logo {
      font-size: 1.8rem;
      font-weight: 700;
      color: var(--primary-color);
      text-decoration: none;
      display: flex;
      align-items: center;
      cursor: pointer;
    }

    .logo span {
      margin-left: 0.5rem;
    }

    .search-container {
      display: flex;
      flex-grow: 1;
      margin: 0 2rem;
      max-width: 600px;
    }

    .search-bar {
      width: 100%;
      padding: 0.8rem 1.5rem;
      border-radius: 30px 0 0 30px;
      border: 1px solid #ddd;
      font-size: 1rem;
      outline: none;
    }

    .search-button {
      background: var(--accent-color);
      color: white;
      border: none;
      padding: 0 1.5rem;
      border-radius: 0 30px 30px 0;
      cursor: pointer;
    }

    .subscribe-btn {
      background: var(--secondary-color);
      color: white;
      border: none;
      padding: 0.8rem 1.5rem;
      border-radius: 30px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s;
    }

    .subscribe-btn:hover {
      background: var(--dark-color);
      transform: translateY(-2px);
    }

    .ticker-container {
      background: var(--dark-color);
      color: white;
      padding: 0.5rem 0;
      overflow: hidden;
      white-space: nowrap;
    }

    .ticker-content {
      display: inline-block;
      animation: ticker 60s linear infinite;
      padding-left: 100%;
    }

    .ticker-item {
      display: inline-block;
      margin-right: 2rem;
      font-size: 0.9rem;
      font-weight: 500;
    }

    .positivo { color: #a5d6a7; }
    .negativo { color: #ef9a9a; }

    @keyframes ticker {
      0% { transform: translateX(0); }
      100% { transform: translateX(-100%); }
    }

    .contenedor-principal {
      max-width: 1200px;
      margin: 2rem auto;
      padding: 0 1rem;
    }

    .categorias-menu {
      background: white;
      padding: 1rem;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      margin-bottom: 2rem;
      position: sticky;
      top: 80px;
      z-index: 999;
    }

    .categorias-lista {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      justify-content: center;
    }

    .categoria-item {
      background: var(--light-color);
      color: var(--dark-color);
      padding: 0.5rem 1rem;
      border-radius: 20px;
      text-decoration: none;
      font-weight: 500;
      transition: all 0.3s;
    }

    .categoria-item:hover {
      background: var(--accent-color);
      color: white;
      transform: translateY(-2px);
    }

    .categoria-seccion {
      margin-bottom: 3rem;
      background: white;
      border-radius: 12px;
      padding: 2rem;
      box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }

    .categoria-titulo {
      color: var(--primary-color);
      margin-top: 0;
      padding-bottom: 1rem;
      border-bottom: 2px solid var(--accent-color);
    }

    .noticias-container {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 2rem;
    }

    .noticia {
      border: 1px solid #eee;
      border-radius: 8px;
      overflow: hidden;
      transition: transform 0.3s;
    }

    .noticia:hover {
      transform: translateY(-5px);
      box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }

    .noticia-imagen {
      width: 100%;
      height: 200px;
      object-fit: cover;
    }

    .noticia-titulo {
      color: var(--primary-color);
      margin: 1rem 1rem 0.5rem;
      font-size: 1.2rem;
    }

    .noticia-meta {
      display: flex;
      justify-content: space-between;
      margin: 0 1rem 1rem;
      font-size: 0.8rem;
      color: #666;
    }

    .noticia-descripcion {
      margin: 0 1rem 1rem;
      color: #555;
      font-size: 0.9rem;
    }

    .noticia-enlace {
      display: inline-block;
      background: var(--secondary-color);
      color: white;
      padding: 0.5rem 1rem;
      border-radius: 20px;
      text-decoration: none;
      margin: 0 1rem 1rem;
      font-size: 0.9rem;
      transition: all 0.3s;
    }

    .noticia-enlace:hover {
      background: var(--primary-color);
    }

    .galeria {
      display: flex;
      gap: 0.5rem;
      margin: 0.5rem;
      overflow-x: auto;
      padding-bottom: 0.5rem;
    }

    .galeria img {
      height: 100px;
      width: auto;
      border-radius: 4px;
      object-fit: cover;
    }

    .modal {
      display: none;
      position: fixed;
      z-index: 1001;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0,0,0,0.5);
    }

    .modal-content {
      background-color: #fefefe;
      margin: 15% auto;
      padding: 2rem;
      border-radius: 8px;
      width: 80%;
      max-width: 500px;
    }

    .close {
      color: #aaa;
      float: right;
      font-size: 1.5rem;
      font-weight: bold;
      cursor: pointer;
    }

    .close:hover {
      color: black;
    }

    .form-group {
      margin-bottom: 1rem;
    }

    .form-group label {
      display: block;
      margin-bottom: 0.5rem;
    }

    .form-group input {
      width: 100%;
      padding: 0.5rem;
      border: 1px solid #ddd;
      border-radius: 4px;
    }

    .form-actions {
      margin-top: 1.5rem;
      text-align: right;
    }

    footer {
      background: var(--dark-color);
      color: white;
      text-align: center;
      padding: 2rem;
      margin-top: 3rem;
    }

    .loading {
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 2rem;
    }

    .spinner {
      width: 40px;
      height: 40px;
      border: 4px solid rgba(0, 0, 0, 0.1);
      border-radius: 50%;
      border-top-color: var(--accent-color);
      animation: spin 1s ease-in-out infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    @media (max-width: 768px) {
      .navbar {
        flex-direction: column;
        padding: 1rem;
      }

      .logo {
        margin-bottom: 1rem;
      }

      .search-container {
        margin: 1rem 0;
        width: 100%;
      }

      .noticias-container {
        grid-template-columns: 1fr;
      }

      .categorias-menu {
        top: 70px;
      }
    }
    </style>
    """
    
    # JavaScript para la búsqueda y funcionalidades
    js = """
    <script>
    // Función para buscar noticias
    function buscarNoticias() {
      const termino = document.getElementById('busqueda').value.toLowerCase();
      const noticias = document.querySelectorAll('.noticia');
      const categorias = document.querySelectorAll('.categoria-seccion');
      
      let resultadosEncontrados = false;
      
      // Buscar en todas las noticias
      noticias.forEach(noticia => {
        const titulo = noticia.querySelector('.noticia-titulo').textContent.toLowerCase();
        const descripcion = noticia.querySelector('.noticia-descripcion').textContent.toLowerCase();
        
        if (titulo.includes(termino) || descripcion.includes(termino)) {
          noticia.style.display = 'block';
          resultadosEncontrados = true;
        } else {
          noticia.style.display = 'none';
        }
      });
      
      // Mostrar/ocultar categorías según resultados
      categorias.forEach(categoria => {
        const noticiasVisibles = categoria.querySelectorAll('.noticia[style="display: block"]');
        if (noticiasVisibles.length > 0) {
          categoria.style.display = 'block';
        } else {
          categoria.style.display = 'none';
        }
      });
      
      // Mostrar mensaje si no hay resultados
      const mensaje = document.getElementById('mensaje-busqueda');
      if (!resultadosEncontrados && termino) {
        mensaje.textContent = `No se encontraron resultados para "${termino}"`;
        mensaje.style.display = 'block';
      } else {
        mensaje.style.display = 'none';
      }
    }
    
    // Función para limpiar la búsqueda
    function limpiarBusqueda() {
      document.getElementById('busqueda').value = '';
      document.querySelectorAll('.noticia').forEach(n => n.style.display = 'block');
      document.querySelectorAll('.categoria-seccion').forEach(c => c.style.display = 'block');
      document.getElementById('mensaje-busqueda').style.display = 'none';
    }
    
    // Función para mostrar el modal de suscripción
    function mostrarModalSuscripcion() {
      document.getElementById('modalSuscripcion').style.display = 'block';
    }
    
    // Función para ocultar el modal
    function ocultarModal() {
      document.getElementById('modalSuscripcion').style.display = 'none';
    }
    
    // Función para manejar el envío del formulario de suscripción
    function suscribirse(event) {
      event.preventDefault();
      const email = document.getElementById('email').value;
      
      if (!email || !email.includes('@')) {
        alert('Por favor ingresa un email válido');
        return;
      }
      
      // Aquí deberías enviar el email al servidor para guardarlo
      // Por ahora solo mostramos un mensaje
      alert(`¡Gracias por suscribirte con ${email}! Recibirás notificaciones de nuevas publicaciones.`);
      ocultarModal();
    }
    
    // Función para recargar la página al hacer clic en el logo
    function recargarPagina() {
      location.reload();
    }
    
    // Actualizar la página cada 2 horas
    setTimeout(function() {
      location.reload();
    }, 7200000);
    
    // Cerrar modal al hacer clic fuera del contenido
    window.onclick = function(event) {
      const modal = document.getElementById('modalSuscripcion');
      if (event.target == modal) {
        ocultarModal();
      }
    }
    </script>
    """
    
    # Modal de suscripción
    modal_html = """
    <div id="modalSuscripcion" class="modal">
      <div class="modal-content">
        <span class="close" onclick="ocultarModal()">&times;</span>
        <h2>Suscríbete a nuestras notificaciones</h2>
        <form onsubmit="suscribirse(event)">
          <div class="form-group">
            <label for="email">Email:</label>
            <input type="email" id="email" required placeholder="tu@email.com">
          </div>
          <div class="form-actions">
            <button type="submit" class="subscribe-btn">Suscribirse</button>
          </div>
        </form>
      </div>
    </div>
    """
    
    # HTML completo
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>InfoDiversa - Todas las categorías</title>
  {css}
</head>
<body>
  <nav class="navbar">
    <div class="logo" onclick="recargarPagina()">📰 <span>InfoDiversa</span></div>
    <div class="search-container">
      <input type="text" id="busqueda" class="search-bar" placeholder="Buscar en todas las categorías...">
      <button class="search-button" onclick="buscarNoticias()">🔍</button>
    </div>
    <button class="subscribe-btn" onclick="mostrarModalSuscripcion()">Suscribirse</button>
  </nav>

  <div class="ticker-container">
    <div class="ticker-content">
      {ticker_items}
    </div>
  </div>

  <div class="contenedor-principal">
    <div class="categorias-menu">
      <div class="categorias-lista">
        {"".join(categorias_html)}
      </div>
    </div>
    
    <div id="mensaje-busqueda" style="display: none; background: #fff3cd; padding: 1rem; border-radius: 8px; margin-bottom: 2rem;"></div>
    
    {"".join(noticias_html)}
  </div>

  {modal_html}

  <footer>
    <p>© {datetime.now().year} InfoDiversa - Todas las categorías</p>
    <p>Actualizado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}</p>
  </footer>
  
  {js}
</body>
</html>
"""
    
    with open(RUTA_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Página HTML generada: {RUTA_HTML}")

def ejecutar_actualizacion():
    """Ejecuta la actualización de noticias y genera el HTML"""
    print("🔄 Actualizando noticias...")
    datos = actualizar_noticias()
    generar_html(datos)
    print("✅ Actualización completada")

def programar_actualizaciones():
    """Programa las actualizaciones periódicas"""
    while True:
        try:
            ejecutar_actualizacion()
            
            # Esperar 1 hora (3600 segundos) antes de la próxima actualización
            time.sleep(3600)
            
            # Si no se encontraron noticias en la última actualización, esperar solo 1 hora adicional
            datos = cargar_datos()
            if not datos.get("noticias"):
                print("⚠️ No se encontraron noticias en la última actualización. Reintentando en 1 hora...")
                time.sleep(3600)
                
        except Exception as e:
            print(f"❌ Error en la actualización: {str(e)}")
            print("Reintentando en 1 hora...")
            time.sleep(3600)

if __name__ == "__main__":
    # Verificar si el archivo de datos existe y está actualizado
    datos = cargar_datos()
    
    # Si no hay datos o la última actualización fue hace más de 1 hora, actualizar
    if not datos.get("noticias") or not datos.get("ultima_actualizacion") or \
       (datetime.now() - datetime.fromisoformat(datos["ultima_actualizacion"])).total_seconds() > 3600:
        ejecutar_actualizacion()
    else:
        generar_html(datos)
    
    # Iniciar hilo para actualizaciones periódicas
    hilo_actualizacion = threading.Thread(target=programar_actualizaciones)
    hilo_actualizacion.daemon = True
    hilo_actualizacion.start()
    
    print(f"🚀 Servicio iniciado. Abre el archivo {RUTA_HTML} en tu navegador.")
    
    # Mantener el programa en ejecución
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Programa terminado por el usuario")