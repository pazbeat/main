# Short (under 2 min) narration for the purchase tutorials, v4: matches the 2026-10 constructor
# (steps Card / Gift / For whom / Salon / Sending / Payment). The text is the same for PC and phone,
# so one ElevenLabs take per language serves both videos.
# Each line: (id, caption, acts, extra); acts is a comma-separated list of recorder actions.
import re

TXT = {
    'ru': {
        'i1': 'Здравствуйте! Покажу, как купить подарочный сертификат «Имбирь» на сайте imbir.kz.',
        'i2': 'Это займёт всего пару минут.',
        'h1': 'Нажмите «Подарить сертификат» — на телефоне эта кнопка в меню.',
        'c1': 'Прочитайте условия покупки, поставьте галочку и нажмите «Принимаю».',
        'd1': 'Шаг первый — открытка. Выберите повод, найдите открытку, которая нравится, и нажмите «Далее».',
        'g1': 'Шаг второй — подарок. Чтобы подарить программу, нажмите на её название на круге — появятся описание и цена.',
        'g2': 'Или подарите сумму — от двадцати до двухсот тысяч тенге.',
        'p1': 'Шаг третий — для кого. Имя получателя и подпись указывать не обязательно — они появятся на сертификате.',
        'p2': 'Можно добавить поздравление до ста символов.',
        'b1': 'Шаг четвёртый — салон. Выберите город и салон. Отдыхать по сертификату можно в любом салоне сети.',
        'e1': 'Шаг пятый — отправка: сразу после оплаты или в выбранную дату.',
        'e2': 'Укажите свою почту — туда придут сертификат и чек. Почту получателя можно добавить по желанию.',
        'y1': 'Шаг шестой — оплата. Проверьте заказ и, если есть промокод, введите его.',
        'y2': 'Выберите Kaspi или карту, отметьте согласие с правилами и нажмите «Оплатить».',
        'a1': 'После оплаты сертификат с QR-кодом придёт на вашу почту.',
        'a2': 'Его статус и баланс можно проверить на сайте.',
        't1': 'Сертификат действует три месяца,',
        't2': 'во всех салонах сети, кроме Imbir Platinum.',
        't3': 'Запишитесь заранее по телефону или в WhatsApp,',
        't5': 'и покажите сертификат администратору.',
        'o1': 'Дарите тепло Таиланда! Ждём вас в салонах «Имбирь».',
    },
    'en': {
        'i1': "Hi! Here's how to buy an Imbir gift certificate on imbir.kz.",
        'i2': 'It only takes a couple of minutes.',
        'h1': 'Press “Gift a certificate” — on a phone, it’s in the menu.',
        'c1': 'Read the terms, tick the box and press “Accept”.',
        'd1': 'Step one — design. Choose an occasion, find a card you like and press “Next”.',
        'g1': "Step two — the gift. To give a program, select its name on the circle — you'll see the description and price.",
        'g2': 'Or give an amount — from twenty to two hundred thousand tenge.',
        'p1': "Step three — who it's for. The recipient's name and your signature are optional; they'll appear on the certificate.",
        'p2': 'You can also add a message of up to one hundred characters.',
        'b1': 'Step four — the salon. Choose a city and a salon. The certificate works at any salon in the network.',
        'e1': 'Step five — sending: right after payment, or on a date you choose.',
        'e2': "Enter your email — the certificate and receipt will arrive there. The recipient's email is optional.",
        'y1': 'Step six — payment. Check your order and enter a promo code if you have one.',
        'y2': 'Choose Kaspi or a bank card, tick the box to accept the rules and press “Pay”.',
        'a1': 'After payment, the certificate arrives by email as a PDF with a QR code.',
        'a2': 'You can check its status and balance on the website.',
        't1': "It's valid for three months,",
        't2': 'at every salon in the network except Imbir Platinum.',
        't3': 'Book in advance by phone or WhatsApp,',
        't5': 'and show the certificate to the administrator.',
        'o1': 'Give the warmth of Thailand. We look forward to seeing you at Imbir!',
    },
    'kk': {
        'i1': 'Сәлеметсіз бе! imbir.kz сайтында «Imbir» сыйлық сертификатын қалай сатып алуға болатынын көрсетемін.',
        'i2': 'Бұған бірнеше минут қана кетеді.',
        'h1': '«Сертификат сыйлау» батырмасын басыңыз — телефонда ол мәзірде орналасқан.',
        'c1': 'Сатып алу шарттарын оқып шығыңыз, құсбелгі қойып, «Қабылдаймын» батырмасын басыңыз.',
        'd1': 'Бірінші қадам — ашықхат. Сыйлау себебін таңдап, ұнаған ашықхатты тауып, «Әрі қарай» батырмасын басыңыз.',
        'g1': 'Екінші қадам — сыйлық. Бағдарлама сыйлау үшін шеңбердегі оның атауын басыңыз — сипаттамасы мен бағасы көрсетіледі.',
        'g2': 'Немесе жиырма мыңнан екі жүз мың теңгеге дейінгі соманы сыйлаңыз.',
        'p1': 'Үшінші қадам — сыйлық кімге. Алушының аты мен сіздің есіміңізді жазу міндетті емес — олар сертификатта көрсетіледі.',
        'p2': 'Жүз таңбаға дейін құттықтау да қосуға болады.',
        'b1': 'Төртінші қадам — салон. Қала мен салонды таңдаңыз. Сертификатпен желінің кез келген салонында демалуға болады.',
        'e1': 'Бесінші қадам — жіберу: төлемнен кейін бірден немесе таңдалған күні.',
        'e2': 'Электрондық поштаңызды жазыңыз — сертификат пен чек сонда келеді. Алушының поштасын жазу міндетті емес.',
        'y1': 'Алтыншы қадам — төлем. Тапсырысты тексеріп, промокодыңыз болса, оны енгізіңіз.',
        'y2': 'Kaspi немесе банк картасын таңдап, ережелермен келісетініңізді белгілеңіз де, «Төлеу» батырмасын басыңыз.',
        'a1': 'Төлемнен кейін QR-коды бар сертификат электрондық поштаңызға келеді.',
        'a2': 'Сертификаттың күйі мен балансын сайттан тексеруге болады.',
        't1': 'Сертификат үш ай бойы жарамды,',
        't2': 'және Imbir Platinum-нан басқа, желінің барлық салонында қабылданады.',
        't3': 'Салонға алдын ала телефон немесе WhatsApp арқылы жазылыңыз,',
        't5': 'және сертификатты әкімшіге көрсетіңіз.',
        'o1': 'Таиланд жылуын сыйлаңыз! Сізді «Imbir» салондарында күтеміз!',
    },
}

ORDER = [
    ('intro', 'g', [('i1', None, {}), ('i2', None, {})]),
    ('home', 's', [('h1', 'home', {})]),
    ('consent', 's', [('c1', 'consent', {})]),
    ('s1', 's', [('d1', 'occasion,designs,next', {'step': 1})]),
    ('s2', 's', [('g1', 'program', {'step': 2}), ('g2', 'amount,next', {'step': 2})]),
    ('s3', 's', [('p1', 'name,from', {'step': 3}), ('p2', 'greeting,next', {'step': 3})]),
    ('s4', 's', [('b1', 'branch,next', {'step': 4})]),
    ('s5', 's', [('e1', 'when_now,when_date', {'step': 5}), ('e2', 'email_buyer,email_rcpt,next', {'step': 5})]),
    ('s6', 's', [('y1', 'summary,promo', {'step': 6}), ('y2', 'paymethod,pay', {'step': 6})]),
    ('after', 'g', [('a1', None, {}), ('a2', None, {})]),
    ('terms', 'g', [('t1', None, {}), ('t2', None, {}), ('t3', None, {}), ('t5', None, {})]),
    ('outro', 'g', [('o1', None, {})]),
]

def flow(lang):
    T = TXT[lang]
    return [(sid, kind, [(lid, T[lid], act, extra) for lid, act, extra in lines]) for sid, kind, lines in ORDER]

def line_ids():
    return [lid for _, _, lines in ORDER for lid, _, _ in lines]

# spoken form for the synthesiser (captions keep the written form)
REPL = {
    'ru': [('imbir.kz', 'имбир точка кей зет'), ('Imbir Platinum', 'Имбир Платинум'), ('«Имбирь»', 'Имбирь'), ('PDF', 'пэ дэ эф'),
           ('WhatsApp', 'ватсап'), ('Kaspi', 'Каспи')],
    'en': [('imbir.kz', 'imbir dot K Z'), ('Imbir Platinum', 'Imbeer Platinum'), ('Imbir', 'Imbeer'), ('PDF', 'P D F'), ('QR code', 'Q R code'),
           ('Kaspi', 'Kaspee')],
    'kk': [('imbir.kz', 'имбир нүкте кей зет'), ('Imbir Platinum-нан', 'Имбир Платинумнан'), ('«Imbir»', 'Имбир'), ('Kaspi', 'Каспи'),
           ('PDF', 'пи ди эф'), ('QR-коды', 'кью ар коды'), ('WhatsApp', 'уатсап')],
}

def spoken(s, lang):
    for a, b in REPL[lang]: s = s.replace(a, b)
    s = s.replace('«', '').replace('»', '').replace('“', '').replace('”', '')
    return re.sub(r'\s+', ' ', s).strip()

if __name__ == '__main__':
    for lang in TXT:
        n = sum(len(spoken(TXT[lang][i], lang)) for i in line_ids())
        print(lang, n, 'chars')
