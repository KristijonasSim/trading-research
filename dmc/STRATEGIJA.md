# Dumb Money Concepts (DMC) – „Dumb Money Hunter“, Maven įkūrėjas

Šaltinis: YouTube grojaraštis „FREE COURSE – Dumb Money Concepts“ (16 video, ~1,5 val.), perskaityti visi transkriptai 2026-11-13.
Autorius pats sako: strategija keičiasi kas kelis mėnesius, senesni video (zonos, DCA) jau pasenę; naujausi – 12–16.

## Esmė vienu sakiniu
Kaina eina nuo lygio iki lygio. Prie kiekvieno lygio žiūri tik vieną dalyką: **ar žvakė UŽSIDARĖ už lygio** (eis iki kito lygio) **ar tik dagtis perlindo ir užsidarė atgal** (apsisuks ir grįš ten, iš kur atėjo).

## 1. Lygiai
- Lygis = **žvakės kūno** kraštas (open/close), ne dagtis. Ypač svarbūs **dar neišbandyti** (kaina jų dar nelietė).
- Žymimi nuo didžiausio laiko rėmo: mėnuo → savaitė → diena → 4 val. → 2 val. → 1 val. → 15 min.
- **Išbandytas kartą** lygis antrą kartą dažniausiai pramušamas – jo nebeimti.
- „Pass-through“ lygiai: senų didelių žvakių kūnai, per kuriuos kaina prabėgo; kuo daugiau kartų perėjo, tuo silpnesnis.
- Prioritetas: aukštesnis laiko rėmas > arčiau kainos > mažiau „perėjimų“.
- Didelėje greitoje žvakėje kaina „peršoka“ smulkius lygius ir jų negrįžta tikrinti.

## 2. Pagrindinė taisyklė (gain / fail)
- **Gain/lose:** žvakė užsidaro už lygio → kaina grįžta trumpai patikrinti to lygio (retest) → eina iki **kito** lygio.
- **Failure to gain/lose:** dagtis perlenda per lygį, bet žvakė užsidaro atgal → kaina eina į priešingą pusę, iki **judesio pradžios** (origin).
- **Reclaim:** kaina užsidarė už lygio, bet vėliau grįžo atgal į zoną – tas pats kaip failure, tik silpniau → taikinys kita zonos pusė.
- „Šono nėra“ – šoninis judėjimas = kaina daužosi nuo vieno krašto prie kito po nepavykusių bandymų.

## 3. Trendas
- Trendas = **kitas judesys aukštesniame laiko rėme** (pvz., savaitinė žvakė atšoko nuo lygio → savaitės „kitas judesys“ aukštyn). Dienos sandoriai – ta kryptimi.
- Trendas keičiasi, kai aukštesnio rėmo žvakė užsidaro už svarbaus lygio priešinga kryptimi.

## 4. Kada neprekiauti – „range lock“
- Aukštesnių rėmų žvakės su ilgomis dagtimis abiejose pusėse (spinning top), dažnai prieš naujienas (FOMC, NFP). Tada arba prekiauti nuo krašto iki krašto, arba laukti išsiveržimo.

## 5. Keli laiko rėmai ir uždarymo laikas
- Lygius žymėti 4h/2h/1h, sandorį sekti 15 min./5 min.
- **Svarbiausia ta žvakė, kuri ką tik užsidarė ir yra didžiausia.** Pvz. NY atidarymo metu 4 val. žvakė jau beveik baigta, todėl svarbesnės 1 val. ir 2 val.
- Jei liko 30 min. iki 4 val. uždarymo, o 15 min. jau rodo kryptį – nelaukti.

## 6. Įėjimas, išėjimas, rizika
- Įėjimas: (a) „aklai“ prie neišbandyto dienos/savaitės/mėnesio lygio; (b) palaukti reakcijos (dagtis/reclaim), tada retest'e; (c) DCA – daugiausiai 1–2 papildomi pirkimai, jokio martingalo.
- Taikinys: **kitas lygis**, dažniausiai ~1–1,5R. Didelių R „ilgų bėgimų“ nesivaikyti – tai „lošimas“.
- Stop: už **kito lygio už savo lygio** (ne tiesiai už jo). Išeiti anksčiau, jei aukštesnio rėmo žvakė užsidaro prieš tave arba žvakė užsidaro „raudonoje zonoje“.
- Rizikos dydis: tiek, kad pralaimėjimas būtų nemalonus, bet nereikėtų nuolat žiūrėti į grafiką.

## 7. „Market open“ variantas (video 14, naujausias, „5 min. per dieną“)
- NASDAQ. Prieš NY atidarymą žiūri **paskutinę 1 val. žvakę**: ar ji pramušė lygį (gain) ar nepavyko (failure).
- Iš to nustato atidarymo kryptį, įeina, kai 5 min. žvakė užsidaro atgal į zoną (arba prie London low/high), taikinys – kitas lygis (naujas high/low). Sandoris trunka kelias minutes.

## Kas įtartina
- Teiginiai „90 % laimėjimų“, „100 % strike rate“, „jei klystu – tai mano klaida, ne strategijos“. Įrodymų (sąskaitos istorijos, backtesto) nėra.
- Daug dalykų sprendžiama „iš akies“: kuris lygis svarbus, kada „range lock“, kada išeiti. Video nuolat nukreipia į live streamus ir Discord.
- Autorius – Maven įkūrėjas, kiekviename video Maven reklama su nuolaidos kodu.

## Ar galima testuoti
Iš dalies. Mechaniškai užrašomas branduolys: neišbandyti kūno lygiai + „užsidarė už / dagtis ir atgal“ + taikinys kitas lygis. Market open variantą (1 val. žvakė prieš 9:30 → kryptis → 5 min. įėjimas) galima išbandyti ant NAS100 1 min. duomenų, kuriuos jau turime.
