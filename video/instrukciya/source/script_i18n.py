# English and Kazakh narration for the purchase tutorials (same line ids / actions as the Russian script).
import re

def flow(device, lang):
    pc = device == 'pc'
    if lang == 'en':
        tap = 'click' if pc else 'tap'; Tap = tap.capitalize()
        L = {
            'i1': "Hello! In this video I'll show you how to buy a gift certificate for the Imbir Thai spa network on imbir.kz.",
            'i2': 'It only takes a couple of minutes.',
            'h1': 'Open imbir.kz and click “Gift a certificate”.' if pc else 'Open imbir.kz, tap the menu in the top right corner and choose “Gift a certificate”.',
            'c1': 'First, a window with the terms of purchase opens. Please read them carefully.',
            'c2': f'Then tick the box and {tap} “Accept”.',
            'd1': 'Step one — design.',
            'd2': 'Choose an occasion, for example “Birthday”.',
            'd3': 'Use the arrows on the sides to browse the cards and pick the one you like.' if pc else 'Swipe through the cards and pick the one you like.',
            'd4': f'Then {tap} “Next”.',
            'g1': 'Step two — the gift. You can give a program or an amount.',
            'g2': 'To give a program, click its name on the circle. The description and price appear on the right.' if pc else 'To give a program, turn the arc and tap its name. The description and price appear at the top.',
            'g3': 'To give an amount, open the “Amount” tab and choose a value — from twenty to two hundred thousand.',
            'g4': f'{Tap} “Next”.',
            'p1': 'Step three — the message.' if pc else 'Step three — the recipient.',
            'p2': "Enter the recipient's name — it will be printed on the certificate.",
            'p3': 'The “From” field is optional.',
            'p4': f'If you like, {tap} “Add a message” and write a few warm words, up to one hundred characters. The message will also appear on the certificate.',
            'p5': f'{Tap} “Next”.',
            'b1': 'Step four — the salon. Choose a city and a salon.',
            'b2': 'Don’t worry: the certificate can be used at any salon in the network.',
            'b3': f'{Tap} “Next”.',
            'e1': 'Step five — delivery. Choose when to send the certificate: right after payment…',
            'e2': '…or on a chosen date and time — for example, on the morning of the celebration.',
            'e3': 'Enter your email. The certificate and the receipt will be sent there, so you can hand it over in person or forward it.',
            'e4': "If you know the recipient's email, enter it in the second field and the certificate will go to them too. This field is optional.",
            'e5': f'{Tap} “Next”.',
            'y1': 'Step six — payment. Check your order details.',
            'y2': f'If you have a promo code, {tap} “Promo code” and enter it — the discount will be applied to the total.',
            'y3': 'Choose a payment method: Kaspi, paying in the app, or a Visa or Mastercard bank card.',
            'y4': f'Tick the box to accept the rules and {tap} “Pay”.',
            'a1': 'After payment, the certificate arrives as a PDF with a QR code at the email you entered — right away or on the chosen date.',
            'a2': "You can check the certificate's status and balance on the website.",
            't0': 'A few important terms.',
            't1': 'The certificate is valid for three months from the date of purchase.',
            't2': 'It is accepted at all salons in the network except Imbir Platinum.',
            't3': 'Book in advance by phone or WhatsApp with the salon — the numbers are on the website.',
            't4': 'Arrive ten to fifteen minutes before the start.',
            't5': 'At the salon, show your certificate to the administrator.',
            't6': 'If a program costs more, pay the difference; if it costs less, the rest stays on the balance.',
            't7': 'Cancel a booking at least three hours in advance, otherwise the service is written off.',
            't8': 'The certificate cannot be exchanged for cash.',
            'o1': "That's it! Give the warmth of Thailand. We look forward to seeing you at our salons!",
        }
    else:
        tap = 'басыңыз' if pc else 'түртіңіз'; tapp = 'басып' if pc else 'түртіп'
        L = {
            'i1': 'Сәлеметсіз бе! Бұл бейнеде imbir.kz сайтында «Imbir» тай спа-салондары желісінің сыйлық сертификатын қалай сатып алуға болатынын көрсетемін.',
            'i2': 'Бұған бар болғаны бірнеше минут кетеді.',
            'h1': 'imbir.kz сайтын ашып, «Сертификат сыйлау» батырмасын басыңыз.' if pc else 'imbir.kz сайтын ашып, жоғарғы оң жақ бұрыштағы мәзірді түртіңіз де, «Сертификат сыйлау» бөлімін таңдаңыз.',
            'c1': 'Алдымен сатып алу шарттары жазылған терезе ашылады. Оларды мұқият оқып шығыңыз.',
            'c2': f'Содан кейін құсбелгі қойып, «Қабылдаймын» батырмасын {tap}.',
            'd1': 'Бірінші қадам — дизайн.',
            'd2': 'Сыйлау себебін таңдаңыз, мысалы, «Туған күн».',
            'd3': 'Бүйірдегі көрсеткілер арқылы ашықхаттарды парақтап, ұнағанын таңдаңыз.' if pc else 'Ашықхаттарды саусақпен сырғытып, ұнағанын таңдаңыз.',
            'd4': f'Содан кейін «Әрі қарай» батырмасын {tap}.',
            'g1': 'Екінші қадам — сыйлық. Бағдарлама немесе белгілі бір соманы сыйлауға болады.',
            'g2': 'Бағдарлама сыйлау үшін шеңбердегі оның атауын басыңыз. Оң жақта сипаттамасы мен бағасы көрсетіледі.' if pc else 'Бағдарлама сыйлау үшін доғаны айналдырып, қажетті атауды түртіңіз. Жоғарыда сипаттамасы мен бағасы көрсетіледі.',
            'g3': 'Сома сыйлау үшін «Сомаға» қойындысын ашып, номиналды таңдаңыз — жиырма мыңнан екі жүз мыңға дейін.',
            'g4': f'«Әрі қарай» батырмасын {tap}.',
            'p1': 'Үшінші қадам — арнау жазуы.' if pc else 'Үшінші қадам — сыйлықты алушы.',
            'p2': 'Алушының атын жазыңыз — ол сертификатқа басылады.',
            'p3': '«Кімнен» өрісін толтыру міндетті емес.',
            'p4': f'Қаласаңыз, «Құттықтау қосу» батырмасын {tapp}, жүз таңбаға дейін жылы лебіз жазыңыз. Құттықтау да сертификатта көрсетіледі.',
            'p5': f'«Әрі қарай» батырмасын {tap}.',
            'b1': ('Төртінші қадам — филиал. Қала мен салонды таңдаңыз.' if pc else 'Төртінші қадам — салон. Қала мен салонды таңдаңыз.'),
            'b2': 'Алаңдамаңыз: сертификатпен желінің кез келген салонында демалуға болады.',
            'b3': f'«Әрі қарай» батырмасын {tap}.',
            'e1': 'Бесінші қадам — жіберу. Сертификаттың қашан жіберілетінін таңдаңыз: төлемнен кейін бірден…',
            'e2': '…немесе өзіңіз таңдаған күн мен уақытта, мысалы, мереке күні таңертең.',
            'e3': 'Электрондық поштаңызды жазыңыз. Сертификат пен чек осы поштаға келеді — сертификатты өзіңіз тапсыра аласыз немесе алушыға жібере аласыз.',
            'e4': 'Алушының электрондық поштасын білсеңіз, оны екінші өріске жазыңыз — сертификат оған да жіберіледі. Бұл өрісті толтыру міндетті емес.',
            'e5': f'«Әрі қарай» батырмасын {tap}.',
            'y1': 'Алтыншы қадам — төлем. Тапсырыс деректерін тексеріңіз.',
            'y2': f'Промокодыңыз болса, «Промокод» батырмасын {tapp}, оны енгізіңіз — жеңілдік тапсырыс сомасына қолданылады.',
            'y3': 'Төлем тәсілін таңдаңыз: Kaspi қосымшасы арқылы немесе Visa не Mastercard банк картасымен.',
            'y4': f'Ережелермен келісетініңізді құсбелгімен растап, «Төлеу» батырмасын {tap}.',
            'a1': 'Төлемнен кейін QR-коды бар PDF сертификат көрсетілген электрондық поштаға келеді — бірден немесе таңдалған күні.',
            'a2': 'Сертификаттың күйі мен балансын сайттан тексеруге болады.',
            't0': 'Бірнеше маңызды шарт.',
            't1': 'Сертификат сатып алынған күннен бастап үш ай бойы жарамды.',
            't2': 'Ол Imbir Platinum салонынан басқа, желінің барлық салонында қабылданады.',
            't3': 'Салонға алдын ала телефон немесе WhatsApp арқылы жазылыңыз — нөмірлер сайтта көрсетілген.',
            't4': 'Бағдарлама басталуынан он-он бес минут бұрын келіңіз.',
            't5': 'Салонда сертификатты әкімшіге көрсетіңіз.',
            't6': 'Бағдарлама сертификат сомасынан қымбат болса, айырмасын төлейсіз; арзан болса, қалдығы балансыңызда сақталады.',
            't7': 'Жазылудан бас тартсаңыз, бұл туралы кемінде үш сағат бұрын хабарлаңыз, әйтпесе қызмет сертификаттан есептен шығарылады.',
            't8': 'Сертификатты қолма-қол ақшаға айырбастауға болмайды.',
            'o1': 'Міне, бәрі осы! Таиланд жылуын сыйлаңыз. Сізді салондарымызда күтеміз!',
        }
    return L

REPL = {
    'en': [('imbir.kz', 'imbir dot K Z'), ('Imbir', 'Imbeer'), ('“', ''), ('”', ''), ('…', ','), (' — ', ', '), ('—', ','), ('WhatsApp', 'WhatsApp'), ('PDF', 'P D F'), ('QR code', 'Q R code')],
    'kk': [('imbir.kz', 'имбир нүкте кей зет'), ('Imbir Platinum', 'Имбир Платинум'), ('Imbir', 'Имбир'), ('«', ''), ('»', ''), ('…', ','), (' — ', ', '), ('—', ','),
           ('Kaspi', 'Каспи'), ('Visa', 'Виза'), ('Mastercard', 'Мастеркард'), ('PDF', 'пи ди эф'), ('QR-коды', 'кью ар коды'), ('Email-іңізді', 'Имейлыңызды'), ('QR-коды', 'кью ар коды'),
           ('WhatsApp', 'уатсап'), ('спа-салондар', 'спа салондар'), ('он-он бес', 'он, он бес'), ('бар-жоғы', 'бар жоғы')],
}

def normalise(s, lang):
    for a, b in REPL[lang]: s = s.replace(a, b)
    s = re.sub(r'\s*,\s*,', ',', s); s = re.sub(r'\s+', ' ', s).strip(' ,')
    return s
