# 免费翻译

import argostranslate.package
import argostranslate.translate


def install_model():

    installed_languages = argostranslate.translate.get_installed_languages()

    for lang in installed_languages:
        if lang.code == "en":
            from_lang = lang

        if lang.code == "zh":
            to_lang = lang

    try:
        from_lang
        to_lang
        return from_lang, to_lang
    except:
        pass

    print("downloading translation model...")

    available_packages = argostranslate.package.get_available_packages()

    package_to_install = None

    for pkg in available_packages:

        if pkg.from_code == "en" and pkg.to_code == "zh":
            package_to_install = pkg
            break

    if package_to_install is None:
        raise Exception("No translation model found")

    download_path = package_to_install.download()

    argostranslate.package.install_from_path(download_path)

    installed_languages = argostranslate.translate.get_installed_languages()

    from_lang = None
    to_lang = None

    for lang in installed_languages:

        if lang.code == "en":
            from_lang = lang

        if lang.code == "zh":
            to_lang = lang

    return from_lang, to_lang


FROM_LANG, TO_LANG = install_model()

TRANSLATOR = FROM_LANG.get_translation(TO_LANG)


def translate(text):
    if not text or not isinstance(text, str):
        return ""
    # 限制长度，避免内存与 API 滥用
    text = text[:500_000]
    chunk_size = 2000

    parts = []

    start = 0

    while start < len(text):

        parts.append(text[start:start + chunk_size])

        start += chunk_size

    result = []

    for p in parts:

        try:
            translated = TRANSLATOR.translate(p)
            result.append(translated)

        except Exception as e:

            print("translate error:", e)

            result.append(p)

    return "\n".join(result)