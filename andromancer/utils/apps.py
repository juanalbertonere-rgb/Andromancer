from andromancer.utils.text import normalize_text

APP_MAP = {
    "whatsapp": "com.whatsapp",
    "chrome": "com.android.chrome",
    "settings": "com.android.settings",
    "ajustes": "com.android.settings",
    "configuracion": "com.android.settings",
    "instagram": "com.instagram.android",
    "twitter": "com.twitter.android",
    "x": "com.twitter.android",
    "gmail": "com.google.android.gm",
    "youtube": "com.google.android.youtube",
    "facebook": "com.facebook.katana",
    "maps": "com.google.android.apps.maps",
    "calendar": "com.google.android.calendar",
    "calendario": "com.google.android.calendar",
    "reloj": "com.google.android.deskclock",
    "clock": "com.google.android.deskclock",
    "calculadora": "com.google.android.calculator",
    "calculator": "com.google.android.calculator",
    "galeria": "com.sec.android.gallery3d",
    "gallery": "com.android.gallery3d",
    "telefono": "com.android.dialer",
    "phone": "com.android.dialer",
    "mensajes": "com.google.android.apps.messaging",
    "messages": "com.google.android.apps.messaging",
    "contactos": "com.android.contacts",
    "contacts": "com.android.contacts",
    "camara": "com.android.camera",
    "camera": "com.android.camera",
    "play store": "com.android.vending",
    "spotify": "com.spotify.music",
    "netflix": "com.netflix.mediaclient",
    "tiktok": "com.zhiliaoapp.musically",
    "home": "HOME",
}

def get_package_name(app_name: str) -> str:
    if not app_name:
        return ""

    norm_name = normalize_text(app_name)
    # Check map first
    if norm_name in APP_MAP:
        return APP_MAP[norm_name]

    return app_name
