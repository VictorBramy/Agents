# מדריך המשך עבודה: Google AI Studio ו-Google Project IDX

שלום! כדי שתוכל להמשיך לעבוד בצורה הנוחה ביותר מהענן, להלן הסבר על שתי האפשרויות המובילות של Google:

---

## אפשרות 1: עבודה עם מודל ה-AI בתוך Google AI Studio (aistudio.google.com)
**Google AI Studio** הוא ממשק ה-Web של גוגל לפיתוח, כוונון ואימון פרומפטים של מודלי Gemini (כגון Gemini 2.5 Flash, Gemini 3.8, Gemini 1.5 Pro).
הוא מיועד להגדרת:
1. **System Instructions** (הנחיות מערכת וחוקי תאריכים נוקשים).
2. **Few-Shot Examples** (דוגמאות אימון קלט-פלט).
3. **Structured Outputs / JSON Schema** (קבלת פלט JSON מובנה).
4. **Tools / Function Calling** (הפעלת פונקציות).

### איך לטעון את הפרויקט ל-Google AI Studio:
1. היכנס ל-[Google AI Studio](https://aistudio.google.com).
2. לחץ על **Create new prompt** (בחר ב-**Structured Prompt** או **System Instructions**).
3. פתח את הקובץ שיצרנו עבורך בפרויקט: [`google_ai_studio_prompt_package.json`](file:///c:/Users/A/Desktop/AGENTS/google_ai_studio_prompt_package.json).
4. העתק את תוכן ה-`system_instruction` לתיבת **System Instructions** ב-AI Studio.
5. תחת **Model Settings** (מימין):
   - בחר במודל: `gemini-2.5-flash` (או `gemini-1.5-pro`).
   - הגדר Temperature: `0.2` (לדיוק מרבי בתאריכים).
   - תחת **Structured Output (JSON)** הדבק את ה-`response_schema` מתוך הקובץ.
6. בלשונית ה-Examples הדבק את דוגמאות ה-Few-shot המופיעות בקובץ.
7. כעת תוכל לבחון כל פרומפט חיפוש (בעברית או באנגלית), לקבל JSON מדויק, וללחוץ על **Get Code** לקבלת קוד Python / cURL ישירות ל-API.

---

## אפשרות 2: עבודה על הקוד המלא בענן (Google Project IDX / GitHub Codespaces)
**Google AI Studio אינו שרת אחסון קוד (Web Host)** — הוא אינו מריץ שרתי FastAPI, בסיס נתונים SQLite או סורקי Playwright. 
אם כוונתך הייתה **להמשיך לפתח ולהריץ את אתר האינטרנט והסוכנים בענן ישירות מהדפדפן**:
גוגל פיתחה לשם כך את **Google Project IDX** (מבוסס ענן ו-VS Code מבית Google):

### איך לפתוח את כל הפרויקט ב-Google Project IDX:
1. נעלה את הקוד ל-GitHub (ריפו פרטי או ציבורי שלך).
2. היכנס ל-[idx.google.com](https://idx.google.com).
3. לחץ על **Import from GitHub** והדבק את כתובת ה-Repository.
4. תוך שניות תפתח לך סביבת פיתוח מלאה בענן של גוגל, כולל טרמינל, שרת Python רץ ודפדפן Preview חי – מכל מחשב או טאבלט!

---

## מה תרצה לעשות עכשיו?
1. האם תרצה שנעלה ונסנכרן את כל הקוד ל-**GitHub** כדי שתוכל לפתוח אותו ב-**Google Project IDX** בקליק אחד?
2. או שברצונך להתמקד בעבודה ישירה מול **Google AI Studio** לבדיקת ועידון הפרומפטים של Gemini?
