"""100 labelled test questions: (expected Jev label, message). Names, phones, ids and dates match clinic.db."""

QUESTIONS = [
    # --- search_patient (9) ---
    ("search_patient", "Can you find the patient with phone number 01012345678?"),
    ("search_patient", "Is Nour Ibrahim registered in your system?"),
    ("search_patient", "Look up the patient record for Youssef Tarek."),
    ("search_patient", "Do you have a patient with the number +20 109 876 5432?"),
    ("search_patient", "What's the patient ID for Khaled Samir?"),
    ("search_patient", "Search for a patient called Laila."),
    ("search_patient", "I think I'm already registered, my number is 0118-765-4321. Can you check?"),
    ("search_patient", "Find patient Ali Gamal please."),
    ("search_patient", "Is there anyone named Mostafa in your patient list?"),

    # --- get_patient_history (10) ---
    ("get_patient_history", "Show me Omar Farouk's past appointments."),
    ("get_patient_history", "What appointments has the patient with phone 01123456789 had?"),
    ("get_patient_history", "Can you pull up the visit history for Mariam Ali?"),
    ("get_patient_history", "When was Laila Mahmoud's last visit and who did she see?"),
    ("get_patient_history", "List all previous visits for phone number 01276543210."),
    ("get_patient_history", "Has Hana Mostafa ever seen Dr. Mona Khalil before?"),
    ("get_patient_history", "I want to see my appointment history, my phone is 01199988877."),
    ("get_patient_history", "How many times has Ali Gamal visited the clinic?"),
    ("get_patient_history", "What did Nour Ibrahim come in for on her recent visits?"),
    ("get_patient_history", "Check Youssef Tarek's appointment record for me."),

    # --- list_doctors (9) ---
    ("list_doctors", "Which doctors work at your clinic?"),
    ("list_doctors", "Do you have an orthodontist?"),
    ("list_doctors", "Who is your pediatric dentist?"),
    ("list_doctors", "I need a root canal specialist - which doctor does endodontics?"),
    ("list_doctors", "List all the dentists and their specialties."),
    ("list_doctors", "Is there a general dentist at the clinic?"),
    ("list_doctors", "What kind of specialists do you have?"),
    ("list_doctors", "My kid needs a dentist, which doctor treats children?"),
    ("list_doctors", "Which doctor should I see for braces?"),

    # --- check_availability (10) ---
    ("check_availability", "Does doctor 1 have any free slots on 2026-10-01?"),
    ("check_availability", "What times are available with Dr. Mona Khalil on October 3rd 2026?"),
    ("check_availability", "Is Dr. Karim Adel free on 2026-09-30?"),
    ("check_availability", "Show me the open slots for doctor 4 on 2026-10-06."),
    ("check_availability", "Any availability with Dr. Ahmed Hassan on 2026-10-07 in the afternoon?"),
    ("check_availability", "When can I see Dr. Salma Youssef on 2026-10-02?"),
    ("check_availability", "Check free times for doctor id 2 on 2026-10-05."),
    ("check_availability", "Are there any morning slots with the endodontist on 2026-10-04?"),
    ("check_availability", "What's open on 2026-10-08 for doctor 3?"),
    ("check_availability", "Is 11:00 free with Dr. Ahmed Hassan on 2026-10-03?"),

    # --- get_treatment_price (10) ---
    ("get_treatment_price", "How much is a teeth cleaning?"),
    ("get_treatment_price", "What does teeth whitening cost?"),
    ("get_treatment_price", "Price of a crown?"),
    ("get_treatment_price", "How much do you charge for a tooth extraction?"),
    ("get_treatment_price", "What's the cost of a regular checkup?"),
    ("get_treatment_price", "How much is a filling?"),
    ("get_treatment_price", "What do you charge for a braces consultation?"),
    ("get_treatment_price", "Is a root canal expensive here? What's the price?"),
    ("get_treatment_price", "Give me the price for whitening and cleaning."),
    ("get_treatment_price", "كم سعر الحشو؟"),

    # --- get_clinic_info (10) ---
    ("get_clinic_info", "Where is the clinic located?"),
    ("get_clinic_info", "Do you accept AXA insurance?"),
    ("get_clinic_info", "Is there parking near the clinic?"),
    ("get_clinic_info", "Are you open on Fridays?"),
    ("get_clinic_info", "What's your cancellation policy?"),
    ("get_clinic_info", "What time do you close on Thursday?"),
    ("get_clinic_info", "Which insurance companies do you work with?"),
    ("get_clinic_info", "What's the clinic's address? I'm coming from Nasr City."),
    ("get_clinic_info", "Do I get charged if I cancel late?"),
    ("get_clinic_info", "العيادة بتفتح الساعة كام؟"),

    # --- book_appointment (10) ---
    ("book_appointment", "I'd like to book a cleaning with Dr. Ahmed Hassan on 2026-10-01 at 10:00. My phone is 01012345678."),
    ("book_appointment", "Book me an appointment with the orthodontist next week."),
    ("book_appointment", "Can I schedule a checkup for my daughter Farida Sherif with Dr. Salma Youssef on 2026-10-06?"),
    ("book_appointment", "I want to make an appointment for a filling."),
    ("book_appointment", "Please reserve slot 5 with doctor 1 for patient 3."),
    ("book_appointment", "Book Khaled Samir with Dr. Karim Adel on 2026-10-02 at 14:00."),
    ("book_appointment", "I need an appointment as soon as possible, I have a toothache. My number is 01211122233."),
    ("book_appointment", "Can I come in tomorrow for a checkup?"),
    ("book_appointment", "Schedule a braces consultation for Nour Ibrahim on 2026-10-05 in the morning."),
    ("book_appointment", "عايز احجز ميعاد كشف مع دكتور احمد حسن"),

    # --- cancel_appointment (8) ---
    ("cancel_appointment", "Please cancel appointment 29."),
    ("cancel_appointment", "I need to cancel my appointment on 2026-10-01, my phone is 01098765432."),
    ("cancel_appointment", "Cancel Hana Mostafa's appointment on October 8th."),
    ("cancel_appointment", "I can't make it to my visit tomorrow, please cancel it."),
    ("cancel_appointment", "Cancel appointment number 36, I'm travelling."),
    ("cancel_appointment", "Khaled Samir wants to cancel his appointment on 2026-10-04."),
    ("cancel_appointment", "Please remove my booking with Dr. Salma Youssef, I'm Laila Mahmoud."),
    ("cancel_appointment", "I want to cancel all my upcoming appointments."),

    # --- reschedule_appointment (8) ---
    ("reschedule_appointment", "Can you move appointment 27 to a different time the same week?"),
    ("reschedule_appointment", "I need to reschedule my appointment on 2026-10-06 with Dr. Karim Adel, my number is 01211122233."),
    ("reschedule_appointment", "Move Mariam Ali's appointment on October 1st to the afternoon."),
    ("reschedule_appointment", "Can I change my appointment to a later date?"),
    ("reschedule_appointment", "Reschedule appointment 31 to slot 450."),
    ("reschedule_appointment", "Something came up - please push my visit on 2026-10-04 to the following day. Phone 01234567890."),
    ("reschedule_appointment", "Can Farida Sherif's appointment on 2026-10-01 be moved to 10 am instead?"),
    ("reschedule_appointment", "I'd like to shift my appointment with Dr. Salma Youssef to next week."),

    # --- register_patient (6) ---
    ("register_patient", "I'm a new patient. My name is Sara Adel, phone 01033344455, born 1998-05-12."),
    ("register_patient", "Please register my son Adam Hussein, phone 01144455566, date of birth 2018-03-03."),
    ("register_patient", "I'd like to sign up as a new patient."),
    ("register_patient", "Add a new patient: Tamer Fawzy, 01566677788, DOB 1980-08-20."),
    ("register_patient", "How do I create a patient file? My name is Rana Said and my number is 01277788899."),
    ("register_patient", "I've never been to your clinic before, can you register me? I'm Mahmoud Ezz, 01011223344, born 1990-01-01."),

    # --- general_chat (10) ---
    ("general_chat", "Hi there!"),
    ("general_chat", "Thank you so much for your help."),
    ("general_chat", "Good morning, how are you?"),
    ("general_chat", "Is it normal for my gums to bleed a little when I floss?"),
    ("general_chat", "What's the difference between a crown and a filling?"),
    ("general_chat", "How often should I get my teeth cleaned?"),
    ("general_chat", "Can you tell me a joke?"),
    ("general_chat", "Bye, have a nice day!"),
    ("general_chat", "Should I brush before or after breakfast?"),
    ("general_chat", "What's the weather like in Cairo today?"),
]

assert len(QUESTIONS) == 100, len(QUESTIONS)
