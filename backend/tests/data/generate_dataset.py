import json
from pathlib import Path

claims = []

# 50 TRUE claims
true_claims = [
    # Technology / Banking (English, Hindi, Marathi, Hinglish)
    ("UPI was developed by NPCI.", "en", "ORGANIZATION", "TIER_1", "Official NPCI / RBI documentation"),
    ("IMPS is available 24 hours a day.", "en", "CURRENT_STATUS", "TIER_1", "NPCI 24/7 service statement"),
    ("RTGS is operated by the Reserve Bank of India.", "en", "ORGANIZATION", "TIER_1", "RBI official website"),
    ("NEFT operates on a 24x7 basis throughout the year.", "en", "CURRENT_STATUS", "TIER_1", "RBI 24x7 circular"),
    ("Unified Payments Interface is an Indian instant payment system.", "en", "FACT", "TIER_1", "NPCI / Government of India"),
    ("BHIM app was developed by National Payments Corporation of India.", "en", "ORGANIZATION", "TIER_1", "NPCI BHIM portal"),
    ("Aadhaar is issued by UIDAI.", "en", "ORGANIZATION", "TIER_1", "UIDAI official portal"),
    ("ISRO launched the Chandrayaan-3 lunar mission.", "en", "EVENT", "TIER_1", "ISRO official release"),
    ("Reserve Bank of India is the central bank of India.", "en", "FACT", "TIER_1", "RBI Act / RBI website"),
    ("SEBI regulates the securities market in India.", "en", "ORGANIZATION", "TIER_1", "SEBI Act / Official website"),
    ("IRDAI regulates insurance in India.", "en", "ORGANIZATION", "TIER_1", "IRDAI official portal"),
    ("PAN card is issued by the Income Tax Department of India.", "en", "ORGANIZATION", "TIER_1", "IT Department official site"),
    ("GST stands for Goods and Services Tax.", "en", "FACT", "TIER_1", "CBIC GST portal"),
    ("India is located in South Asia.", "en", "LOCATION", "TIER_1", "Survey of India / UN geographic data"),
    ("New Delhi is the capital of India.", "en", "LOCATION", "TIER_1", "Government of India official portal"),
    ("India's national animal is the Bengal tiger.", "en", "FACT", "TIER_1", "Know India Portal, GoI"),
    ("India's national bird is the Indian peacock.", "en", "FACT", "TIER_1", "Know India Portal, GoI"),
    ("The national currency of India is the Indian Rupee.", "en", "FACT", "TIER_1", "RBI official site"),
    ("NITI Aayog replaced the Planning Commission.", "en", "ORGANIZATION", "TIER_1", "Cabinet Secretariat notification"),
    ("Supreme Court of India is the highest judicial forum in India.", "en", "FACT", "TIER_1", "Supreme Court of India portal"),
    ("The President of India is the ceremonial head of state.", "en", "PERSON", "TIER_1", "Constitution of India"),
    ("Lok Sabha is the lower house of India's Parliament.", "en", "ORGANIZATION", "TIER_1", "Parliament of India"),
    ("Rajya Sabha is the upper house of India's Parliament.", "en", "ORGANIZATION", "TIER_1", "Parliament of India"),
    ("PM Kisan provides income support to farmers in India.", "en", "POLICY", "TIER_1", "Ministry of Agriculture PM-Kisan portal"),
    ("Ayushman Bharat PM-JAY is a health assurance scheme.", "en", "POLICY", "TIER_1", "National Health Authority"),
    # Hindi True
    ("यूपीआई एनपीसीआई द्वारा विकसित किया गया था।", "hi", "ORGANIZATION", "TIER_1", "NPCI / PIB Hindi release"),
    ("भारत की राजधानी नई दिल्ली है।", "hi", "LOCATION", "TIER_1", "भारत सरकार पोर्टल"),
    ("भारतीय रिजर्व बैंक भारत का केंद्रीय बैंक है।", "hi", "ORGANIZATION", "TIER_1", "आरबीआई हिंदी पोर्टल"),
    ("आधार कार्ड यूआईडीएआई द्वारा जारी किया जाता है।", "hi", "ORGANIZATION", "TIER_1", "यूआईडीएआई पोर्टल"),
    ("इसरो ने चंद्रयान-3 मिशन लॉन्च किया था।", "hi", "EVENT", "TIER_1", "इसरो आधिकारिक प्रेस विज्ञप्ति"),
    ("भारत का राष्ट्रीय पशु बाघ है।", "hi", "FACT", "TIER_1", "भारत राष्ट्रीय पोर्टल"),
    ("भारत का राष्ट्रीय पक्षी मोर है।", "hi", "FACT", "TIER_1", "भारत राष्ट्रीय पोर्टल"),
    ("जीएसटी का अर्थ वस्तु एवं सेवा कर है।", "hi", "FACT", "TIER_1", "सीबीआईसी आधिकारिक पोर्टल"),
    ("नीति आयोग की स्थापना 2015 में हुई थी।", "hi", "DATE", "TIER_1", "कैबिनेट अधिसूचना"),
    ("सुप्रीम कोर्ट भारत की सर्वोच्च अदालत है।", "hi", "ORGANIZATION", "TIER_1", "भारत का सर्वोच्च न्यायालय"),
    # Marathi True
    ("यूपीआय एनपीसीआयने विकसित केले आहे.", "mr", "ORGANIZATION", "TIER_1", "NPCI अधिकृत माहिती"),
    ("भारताची राजधानी नवी दिल्ली आहे.", "mr", "LOCATION", "TIER_1", "भारत सरकार अधिकृत संकेतस्थळ"),
    ("भारतीय रिझर्व्ह बँक ही भारताची मध्यवर्ती बँक आहे.", "mr", "ORGANIZATION", "TIER_1", "आरबीआय अधिकृत संकेतस्थळ"),
    ("भारताचा राष्ट्रीय प्राणी वाघ आहे.", "mr", "FACT", "TIER_1", "अधिकृत राष्ट्रीय पोर्टल"),
    ("इस्रो ही भारताची अंतराळ संशोधन संस्था आहे.", "mr", "ORGANIZATION", "TIER_1", "इस्रो अधिकृत संकेतस्थळ"),
    ("आधार कार्ड UIDAI द्वारे दिले जाते.", "mr", "ORGANIZATION", "TIER_1", "UIDAI अधिकृत पोर्टल"),
    ("महाराष्ट्राची राजधानी मुंबई आहे.", "mr", "LOCATION", "TIER_1", "महाराष्ट्र शासन संकेतस्थळ"),
    # Hinglish True
    ("UPI ko NPCI ne develop kiya hai.", "hi", "ORGANIZATION", "TIER_1", "NPCI official documentation"),
    ("India ki capital New Delhi hai.", "hi", "LOCATION", "TIER_1", "GoI official portal"),
    ("ISRO ne Chandrayaan 3 launch kiya tha.", "hi", "EVENT", "TIER_1", "ISRO official release"),
    ("Aadhaar card UIDAI issue karta hai.", "hi", "ORGANIZATION", "TIER_1", "UIDAI official portal"),
    ("RBI India ka central bank hai.", "hi", "ORGANIZATION", "TIER_1", "RBI official portal"),
    ("IMPS 24 ghante chalne wali payment service hai.", "hi", "CURRENT_STATUS", "TIER_1", "NPCI official circular"),
    ("Tiger India ka national animal hai.", "hi", "FACT", "TIER_1", "Know India Portal"),
    ("Bhim app NPCI ne banaya hai.", "hi", "ORGANIZATION", "TIER_1", "NPCI official site"),
]

for idx, (claim, lang, c_type, src_type, chars) in enumerate(true_claims, start=1):
    claims.append({
        "claim_id": f"eval_true_{idx:03d}",
        "claim_text": claim,
        "language": lang,
        "claim_type": c_type,
        "expected_verdict": "VERIFIED",
        "expected_source_type": src_type,
        "expected_evidence_characteristics": chars
    })

# 50 FALSE claims
false_claims = [
    ("UPI was developed by NASA.", "en", "ORGANIZATION", "TIER_1", "NPCI / PIB official contradiction"),
    ("IMPS only works during bank working hours.", "en", "CURRENT_STATUS", "TIER_1", "NPCI 24/7 round the clock evidence"),
    ("India's national animal is the lion.", "en", "FACT", "TIER_1", "Tiger is national animal, GoI source"),
    ("Reserve Bank of India was founded in 2020.", "en", "DATE", "TIER_1", "RBI was founded in 1935, RBI Act"),
    ("Aadhaar card is issued by the United Nations.", "en", "ORGANIZATION", "TIER_1", "UIDAI issues Aadhaar, not UN"),
    ("ISRO is an agency of the United States Government.", "en", "ORGANIZATION", "TIER_1", "ISRO is Government of India agency"),
    ("Unified Payments Interface has been completely banned across India.", "en", "POLICY", "TIER_1", "PIB / NPCI denial of ban rumor"),
    ("The currency of India is the United States Dollar.", "en", "FACT", "TIER_1", "Indian Rupee is legal tender"),
    ("SEBI regulates traffic signals in Mumbai.", "en", "ORGANIZATION", "TIER_1", "SEBI regulates securities markets"),
    ("PM Kisan offers 10 lakh rupees monthly to every citizen.", "en", "NUMBER", "TIER_1", "PM-Kisan is 6000 INR per year"),
    ("World Health Organization is the central bank of India.", "en", "ORGANIZATION", "TIER_1", "RBI is central bank of India"),
    ("Chandrayaan-3 landed on Mars.", "en", "EVENT", "TIER_1", "Chandrayaan-3 landed on Moon"),
    ("GST was introduced in India in 1947.", "en", "DATE", "TIER_1", "GST introduced in 2017"),
    ("NITI Aayog was established by the British Empire in 1850.", "en", "DATE", "TIER_1", "NITI Aayog established in 2015"),
    ("Supreme Court of India is located in London.", "en", "LOCATION", "TIER_1", "Located in New Delhi"),
    ("India has no Constitution.", "en", "FACT", "TIER_1", "Constitution of India enacted 1950"),
    ("Mumbai is the capital of Tamil Nadu.", "en", "LOCATION", "TIER_1", "Chennai is capital of Tamil Nadu"),
    ("Indian Railways is operated by Apple Inc.", "en", "ORGANIZATION", "TIER_1", "Operated by Ministry of Railways"),
    ("COVID-19 vaccines cause immediate cellular WiFi generation.", "en", "FACT", "TIER_2", "WHO / Fact-check debunking"),
    ("Drinking boiled kerosene completely cures all viral infections.", "en", "FACT", "TIER_2", "Medical refutation / toxic substance"),
    ("The Parliament of India consists of only one member.", "en", "NUMBER", "TIER_1", "Constitutional refutation"),
    ("Aadhaar number has 50 digits.", "en", "NUMBER", "TIER_1", "Aadhaar is 12 digits"),
    ("ATM cash withdrawals will be permanently abolished from midnight.", "en", "POLICY", "TIER_1", "PIB fact check refutation"),
    ("Google founded the Reserve Bank of India.", "en", "ORGANIZATION", "TIER_1", "RBI Act 1934 refutation"),
    ("Indian flag has twenty colors.", "en", "NUMBER", "TIER_1", "Tricolour specification, GoI"),
    # Hindi False
    ("यूपीआई को नासा ने बनाया है।", "hi", "ORGANIZATION", "TIER_1", "एनपीसीआई द्वारा विकसित"),
    ("भारत का राष्ट्रीय पशु शेर है।", "hi", "FACT", "TIER_1", "भारत का राष्ट्रीय पशु बाघ है"),
    ("आरबीआई की स्थापना 2022 में हुई थी।", "hi", "DATE", "TIER_1", "1935 में स्थापना हुई"),
    ("आधार कार्ड अमेरिका की सरकार देती है।", "hi", "ORGANIZATION", "TIER_1", "यूआईडीएआई जारी करता है"),
    ("चंद्रयान 3 मंगल ग्रह पर उतरा था।", "hi", "EVENT", "TIER_1", "चंद्रमा पर उतरा था"),
    ("भारत में कल से 500 रुपये के नोट बंद हो रहे हैं।", "hi", "POLICY", "TIER_1", "पीआईबी फैक्ट चेक खंडन"),
    ("इसरो रूस की एक निजी कंपनी है।", "hi", "ORGANIZATION", "TIER_1", "भारत सरकार की संस्था"),
    ("भारत की राजधानी टोक्यो है।", "hi", "LOCATION", "TIER_1", "राजधानी नई दिल्ली है"),
    ("जीएसटी 1920 में लागू हुआ था।", "hi", "DATE", "TIER_1", "2017 में लागू"),
    ("नीति आयोग क्रिकेट बोर्ड का संचालन करता है।", "hi", "ORGANIZATION", "TIER_1", "नीति निर्माण थिंक टैंक"),
    # Marathi False
    ("यूपीआय नासाने विकसित केले आहे.", "mr", "ORGANIZATION", "TIER_1", "NPCI ने विकसित केले"),
    ("भारताचा राष्ट्रीय प्राणी सिंह आहे.", "mr", "FACT", "TIER_1", "वाघ हा राष्ट्रीय प्राणी आहे"),
    ("आरबीआय अमेरिकेची बँक आहे.", "mr", "ORGANIZATION", "TIER_1", "भारताची मध्यवर्ती बँक"),
    ("महाराष्ट्राची राजधानी कोलकाता आहे.", "mr", "LOCATION", "TIER_1", "मुंबई ही राजधानी आहे"),
    ("आधार कार्ड 100 अंकी असते.", "mr", "NUMBER", "TIER_1", "आधार 12 अंकी असते"),
    ("इस्रो ही खाजगी सॉफ्टवेअर कंपनी आहे.", "mr", "ORGANIZATION", "TIER_1", "अंतराळ संशोधन संस्था"),
    ("भारतात सर्व बँका कायमच्या बंद झाल्या आहेत.", "mr", "CURRENT_STATUS", "TIER_1", "पीआयबी / आरबीआय खंडन"),
    # Hinglish False
    ("UPI ko NASA ne develop kiya hai.", "hi", "ORGANIZATION", "TIER_1", "NPCI developed UPI"),
    ("India ka national animal lion hai.", "hi", "FACT", "TIER_1", "Bengal Tiger is national animal"),
    ("Kal se 500 ke saare note ban ho rahe hain.", "hi", "POLICY", "TIER_1", "PIB Fact Check"),
    ("Aadhaar card Elon Musk ne issue kiya hai.", "hi", "ORGANIZATION", "TIER_1", "UIDAI issue karta hai"),
    ("ISRO America ki space agency hai.", "hi", "ORGANIZATION", "TIER_1", "India's space agency"),
    ("Chandrayaan 3 Sun pe land hua tha.", "hi", "EVENT", "TIER_1", "Moon pe land hua"),
    ("IMPS sirf bank timing me kaam karta hai.", "hi", "CURRENT_STATUS", "TIER_1", "24/7 kaam karta hai"),
    ("UPI pe kal se guaranteed 20% tax lagega.", "hi", "NUMBER", "TIER_1", "PIB / NPCI denial"),
]

for idx, (claim, lang, c_type, src_type, chars) in enumerate(false_claims, start=1):
    claims.append({
        "claim_id": f"eval_false_{idx:03d}",
        "claim_text": claim,
        "language": lang,
        "claim_type": c_type,
        "expected_verdict": "FALSE",
        "expected_source_type": src_type,
        "expected_evidence_characteristics": chars
    })

# 25 PARTLY_SUPPORTED claims
partly_claims = [
    ("UPI was developed by NPCI in 1995.", "en", "DATE", "TIER_1", "NPCI developed UPI is true, but in 2016, not 1995"),
    ("NITI Aayog was formed under Prime Minister Narendra Modi in 1998.", "en", "DATE", "TIER_1", "NITI Aayog formed under PM Modi is true, but in 2015"),
    ("ISRO launched Chandrayaan-3 using an Apollo rocket.", "en", "EVENT", "TIER_1", "ISRO launched Chandrayaan-3 is true, but using LVM3 rocket"),
    ("Reserve Bank of India is in Mumbai and is owned by a private bank.", "en", "ORGANIZATION", "TIER_1", "HQ in Mumbai is true, fully owned by Government of India"),
    ("Aadhaar is a 12-digit number issued by the Ministry of External Affairs.", "en", "ORGANIZATION", "TIER_1", "12-digit is true, issued by UIDAI"),
    ("India's national bird is the peacock which is found only in Antarctica.", "en", "FACT", "TIER_1", "Peacock is national bird is true, not native to Antarctica"),
    ("IMPS is operated 24x7 by the World Bank.", "en", "ORGANIZATION", "TIER_1", "24x7 is true, operated by NPCI"),
    ("GST has multiple slabs and replaced all global tariffs.", "en", "POLICY", "TIER_1", "Multiple slabs is true, replaced Indian indirect taxes"),
    ("Supreme Court of India has judges appointed by the United Nations.", "en", "ORGANIZATION", "TIER_1", "Has judges is true, appointed by President of India"),
    ("Indian Rupee symbol was designed by Udaya Kumar in 1820.", "en", "DATE", "TIER_1", "Designed by Udaya Kumar is true, in 2010"),
    ("UPI supports peer to peer transactions exclusively between government officials.", "en", "RELATIONSHIP", "TIER_1", "Supports P2P is true, open to public"),
    ("BHIM app was launched in 2016 by Steve Jobs.", "en", "PERSON", "TIER_1", "Launched in 2016 is true, launched by PM Narendra Modi"),
    ("Ayushman Bharat covers hospitalization expenses up to 100 crore rupees per family.", "en", "NUMBER", "TIER_1", "Covers hospitalization is true, limit is 5 lakh"),
    ("PM Kisan transfers 6,000 rupees weekly to eligible farmer accounts.", "en", "DATE", "TIER_1", "Transfers 6000 INR is true, yearly in 3 instalments"),
    ("New Delhi is the national capital and has a population of 5 trillion people.", "en", "NUMBER", "TIER_1", "Capital is true, number is exaggerated"),
    # Hindi Partly Supported
    ("यूपीआई एनपीसीआई ने 1990 में बनाया था।", "hi", "DATE", "TIER_1", "एनपीसीआई ने बनाया सच है, 2016 में"),
    ("इसरो ने चंद्रयान 3 नासा के रॉकेट से भेजा था।", "hi", "ORGANIZATION", "TIER_1", "चंद्रयान 3 सच, रॉकेट एलवीएम3 था"),
    ("आधार कार्ड 12 अंकों का होता है और इसे गृह मंत्रालय बनाता है।", "hi", "ORGANIZATION", "TIER_1", "12 अंक सच, यूआईडीएआई बनाता है"),
    ("भारत का राष्ट्रीय पशु बाघ है जो सिर्फ समुद्र में रहता है।", "hi", "FACT", "TIER_1", "बाघ राष्ट्रीय पशु सच, जमीन पर रहता है"),
    ("आरबीआई का मुख्यालय मुंबई में है और यह एक निजी विदेशी कंपनी है।", "hi", "ORGANIZATION", "TIER_1", "मुंबई सच, सरकारी संस्था"),
    # Marathi Partly Supported
    ("यूपीआय एनपीसीआयने 1999 मध्ये सुरू केले.", "mr", "DATE", "TIER_1", "एनपीसीआयने सुरू केले खरे, वर्ष 2016"),
    ("महाराष्ट्राची राजधानी मुंबई असून ती आफ्रिकेत आहे.", "mr", "LOCATION", "TIER_1", "मुंबई राजधानी खरी, भारतात आहे"),
    ("आधार कार्ड 12 अंकी असते आणि ते पोस्ट ऑफिस बनवते.", "mr", "ORGANIZATION", "TIER_1", "12 अंकी खरे, UIDAI जारी करते"),
    # Hinglish Partly Supported
    ("UPI NPCI ne 2005 me launch kiya tha.", "hi", "DATE", "TIER_1", "NPCI launch is true, 2016 me hua"),
    ("Aadhaar 12 digit ka hota hai aur usse FBI issue karti hai.", "hi", "ORGANIZATION", "TIER_1", "12 digit true, UIDAI issue karti hai"),
]

for idx, (claim, lang, c_type, src_type, chars) in enumerate(partly_claims, start=1):
    claims.append({
        "claim_id": f"eval_partly_{idx:03d}",
        "claim_text": claim,
        "language": lang,
        "claim_type": c_type,
        "expected_verdict": "PARTLY_SUPPORTED",
        "expected_source_type": src_type,
        "expected_evidence_characteristics": chars
    })

# 25 OUTDATED claims
outdated_claims = [
    ("Planning Commission formulates five-year plans for India currently.", "en", "CURRENT_STATUS", "TIER_1", "Replaced by NITI Aayog in 2015"),
    ("1000 rupee currency notes are valid legal tender in India today.", "en", "POLICY", "TIER_1", "Demonetised in Nov 2016, RBI notification"),
    ("Jammu and Kashmir is governed under Article 370 of the Indian Constitution.", "en", "POLICY", "TIER_1", "Abrogated in August 2019"),
    ("NEFT operates only during bank working hours on weekdays.", "en", "CURRENT_STATUS", "TIER_1", "Operates 24x7 since December 2019"),
    ("RTGS is available only from 7 AM to 6 PM on working days.", "en", "CURRENT_STATUS", "TIER_1", "Operates 24x7 since December 2020"),
    ("India is currently ruled by the British East India Company.", "en", "CURRENT_STATUS", "TIER_1", "Historical power ended in 1858"),
    ("Pratibha Patil is the current serving President of India.", "en", "PERSON", "TIER_1", "Served 2007-2012, Droupadi Murmu is current"),
    ("Manmohan Singh is the current Prime Minister of India.", "en", "PERSON", "TIER_1", "Served 2004-2014, Narendra Modi is current"),
    ("Urjit Patel is the current Governor of the Reserve Bank of India.", "en", "PERSON", "TIER_1", "Shaktikanta Das succeeded him"),
    ("India has 29 states and 7 union territories.", "en", "NUMBER", "TIER_1", "Changed following J&K Reorganisation Act 2019"),
    ("Service tax of 15% is levied on restaurant bills in India today.", "en", "POLICY", "TIER_1", "Subsumed under GST in 2017"),
    ("Rail Budget is presented separately from the Union Budget.", "en", "POLICY", "TIER_1", "Merged with Union Budget from 2017"),
    ("Planning Commission is headed by Montek Singh Ahluwalia right now.", "en", "PERSON", "TIER_1", "Commission dissolved in 2014"),
    ("Income tax exemption limit is 50,000 rupees per year.", "en", "NUMBER", "TIER_1", "Historical tax slab from decades ago"),
    ("Doordarshan is the sole television broadcaster in India.", "en", "CURRENT_STATUS", "TIER_1", "Privatisation allowed satellite TV since 1990s"),
    # Hindi Outdated
    ("भारत में 1000 रुपये के नोट अभी भी वैध हैं।", "hi", "POLICY", "TIER_1", "2016 में बंद हो चुके हैं"),
    ("योजना आयोग अभी भी भारत के लिए योजनाएं बना रहा है।", "hi", "CURRENT_STATUS", "TIER_1", "2015 में नीति आयोग बना"),
    ("मनमोहन सिंह भारत के वर्तमान प्रधानमंत्री हैं।", "hi", "PERSON", "TIER_1", "नरेंद्र मोदी वर्तमान पीएम हैं"),
    ("जम्मू कश्मीर में आज भी अनुच्छेद 370 लागू है।", "hi", "POLICY", "TIER_1", "2019 में निष्प्रभावी किया गया"),
    ("एनईएफटी केवल बैंक समय में चलता है।", "hi", "CURRENT_STATUS", "TIER_1", "दिसंबर 2019 से 24x7 उपलब्ध"),
    # Marathi Outdated
    ("भारतात 1000 च्या नोटा अजूनही चलनात आहेत.", "mr", "POLICY", "TIER_1", "2016 मध्ये बंद झाल्या"),
    ("नियोजन आयोग भारताचे बजेट ठरवतो.", "mr", "CURRENT_STATUS", "TIER_1", "नीती आयोगाने जागा घेतली"),
    ("मनमोहन सिंग भारताचे विद्यमान पंतप्रधान आहेत.", "mr", "PERSON", "TIER_1", "माजी पंतप्रधान आहेत"),
    # Hinglish Outdated
    ("1000 ka note abhi bhi chalta hai market me.", "hi", "POLICY", "TIER_1", "2016 me demonetise ho gaya"),
    ("Planning Commission abhi bhi 5-year plan banata hai.", "hi", "CURRENT_STATUS", "TIER_1", "NITI Aayog ban chuka hai"),
]

for idx, (claim, lang, c_type, src_type, chars) in enumerate(outdated_claims, start=1):
    claims.append({
        "claim_id": f"eval_outdated_{idx:03d}",
        "claim_text": claim,
        "language": lang,
        "claim_type": c_type,
        "expected_verdict": "OUTDATED",
        "expected_source_type": src_type,
        "expected_evidence_characteristics": chars
    })

# 25 CANNOT_BE_CONFIRMED claims
unconfirmed_claims = [
    ("Aliens secretly landed in a remote village of Rajasthan last night.", "en", "EVENT", "TIER_4", "No credible official report or documentation"),
    ("NPCI secret committee plans to shut down UPI on an undisclosed secret date.", "en", "EVENT", "TIER_1", "Unverifiable secret internal speculation"),
    ("An unknown citizen found a trillion carat diamond in their private backyard yesterday.", "en", "EVENT", "TIER_4", "No credible corroboration"),
    ("Ancient time machines are hidden inside a secret underground bunker in Pune.", "en", "LOCATION", "TIER_4", "Conspiracy claim with no factual grounding"),
    ("A confidential private meeting occurred between unnamed officials about a mystery tax.", "en", "POLICY", "TIER_4", "Vague unsubstantiated rumor"),
    ("Telepathic communication was achieved by a secret laboratory in Kerala yesterday.", "en", "EVENT", "TIER_4", "Pseudoscientific unverifiable assertion"),
    ("The exact number of pebbles on Earth is exactly 938,201,849,203,111.", "en", "NUMBER", "TIER_4", "Unverifiable arbitrary count"),
    ("Every smartphone in India will emit purple light tomorrow at 3:15 AM.", "en", "EVENT", "TIER_4", "Unfounded viral prediction"),
    ("A mystery bird with crystal wings was sighted in the Himalayas.", "en", "FACT", "TIER_4", "Mythological / folklore unconfirmed rumor"),
    ("An anonymous hacker claims to hold the private dreams of all bank managers.", "en", "FACT", "TIER_4", "Immeasurable claim"),
    ("A private unreleased document states that trees secretly talk in binary code.", "en", "FACT", "TIER_4", "Unverifiable assertion"),
    ("Underwater mermaids held a conference near the Mumbai coastline last week.", "en", "EVENT", "TIER_4", "Fictional unverifiable rumor"),
    ("Government of India will replace all roads with chocolate in 2099.", "en", "POLICY", "TIER_4", "Absurd future prediction"),
    ("A subterranean kingdom exists exactly 5 kilometers beneath Bengaluru airport.", "en", "LOCATION", "TIER_4", "Mythological / unsubstantiated claim"),
    ("A hidden radio signal from Jupiter predicted the winner of next year local election.", "en", "EVENT", "TIER_4", "Astrological / unverifiable prophecy"),
    # Hindi Cannot Be Confirmed
    ("कल रात राजस्थान के एक गांव में गुप्त एलियंस उतरे थे।", "hi", "EVENT", "TIER_4", "कोई आधिकारिक प्रमाण नहीं"),
    ("पुणे के एक गुप्त बंकर में टाइम मशीन छिपी हुई है।", "hi", "LOCATION", "TIER_4", "अपुष्ट अफवाह"),
    ("कल सुबह ठीक 4 बजे सभी फोन से बैंगनी रोशनी निकलेगी।", "hi", "EVENT", "TIER_4", "निराधार भविष्यवाणी"),
    ("हिमालय में क्रिस्टल के पंखों वाला पक्षी देखा गया है।", "hi", "FACT", "TIER_4", "काल्पनिक दावा"),
    ("एक अज्ञात व्यक्ति को अपने आंगन में एक खरब कैरेट का हीरा मिला।", "hi", "EVENT", "TIER_4", "कोई स्वतंत्र पुष्टि नहीं"),
    # Marathi Cannot Be Confirmed
    ("काल रात्री गुप्त परग्रहवासी महाराष्ट्रातील एका शेतात उतरले.", "mr", "EVENT", "TIER_4", "कोणताही पुरावा नाही"),
    ("पुण्यातील एका तळघरात गुप्त टाईम मशीन सापडली आहे.", "mr", "LOCATION", "TIER_4", "अफवा, पुरावा नाही"),
    ("उद्या सकाळी सर्व मोबाईलमधून जांभळा प्रकाश बाहेर पडेल.", "mr", "EVENT", "TIER_4", "अपुष्ट व्हायरल मेसेज"),
    # Hinglish Cannot Be Confirmed
    ("Secret aliens kal raat Rajasthan me land huye the.", "hi", "EVENT", "TIER_4", "No official source"),
    ("Pune ke secret bunker me time machine rakhi hai.", "hi", "LOCATION", "TIER_4", "Unconfirmed rumor"),
]

for idx, (claim, lang, c_type, src_type, chars) in enumerate(unconfirmed_claims, start=1):
    claims.append({
        "claim_id": f"eval_unconfirmed_{idx:03d}",
        "claim_text": claim,
        "language": lang,
        "claim_type": c_type,
        "expected_verdict": "CANNOT_BE_CONFIRMED",
        "expected_source_type": src_type,
        "expected_evidence_characteristics": chars
    })

output_path = Path("/Users/tanaypatil/Desktop/Hackthons/SachCheck/backend/tests/data/evaluation_dataset.json")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(claims, f, ensure_ascii=False, indent=2)

print(f"Generated {len(claims)} evaluation claims in {output_path}")
counts = {}
for c in claims:
    v = c["expected_verdict"]
    counts[v] = counts.get(v, 0) + 1
print("Counts by verdict:", counts)
