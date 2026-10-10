# CampusLoop — 2-minute judge walkthrough

## The problem
Students often have useful things they no longer need: textbooks, notes, lamps, small gadgets, stationery, and sports gear. Other students may need the same items at a lower price. A campus-based exchange can reduce waste and make these items easier to find locally.

## The solution
CampusLoop is a student-to-student marketplace prototype. Students can browse sample listings, filter items, create a listing, get help improving a description with Gemma, ask for photo-quality feedback, and draft a polite buyer inquiry. It encourages meetups at public campus locations.

## What to demo live

1. **Browse:** point to the six sample items and use the search/category filter.
2. **Sell:** add a sample item using a nickname, price, condition, and pickup point. Explain that it appears in the current app session only.
3. **AI description:** enter a title and description, then click **Improve with Gemma**. This click sends one prompt using `ask()`.
4. **Photo help:** upload a product image and click **Review photo with Gemma**. This uses `ask_with_image()` for one model inference.
5. **Buyer message:** choose an item, enter a nickname if desired, and click **Draft a buyer message with Gemma**. This uses `make_chat()` and sends one message.

AI features need a valid key in `.env`. Listing creation and browsing work without calling Gemma.

## How to explain the code in plain English

### `app.py`
- Imports Gradio to build the web page and `html.escape` to safely display text typed by users.
- Defines categories, pickup spots, and sample listings so the page has content on first launch.
- `render_listings()` searches the temporary list, filters by category, escapes user content, and produces item cards.
- `listing_choices()` turns every listing into a readable dropdown option while keeping a stable internal ID.
- `add_listing()` checks required fields and price, then adds a new item to Gradio session state. It does not write a database file.
- `improve_description()` builds a clear instruction prompt and calls `ask()` exactly once after the button is clicked.
- `review_photo()` checks that an image exists and calls `ask_with_image()` exactly once after the photo button is clicked.
- `draft_buyer_message()` finds the selected listing, builds a short message prompt, creates a fresh chat with `make_chat()`, and sends one message.
- `CSS` styles the page. The `gr.Blocks` section arranges all controls on one screen/page and connects buttons and filters to the functions above.
- `demo.launch()` starts the local web app.

### `gemma_client.py`
- Loads `.env` with `python-dotenv`.
- Reads `GEMINI_API_KEY` from the environment. It never prints or embeds the key in the source code.
- Keeps the exact required model string `gemma-4-26b-a4b-it` in one constant.
- `ask()` sends one text prompt to the fixed model.
- `ask_with_image()` uploads the selected image, makes one model inference with the image and prompt, and attempts to delete the temporary uploaded file afterward.
- `make_chat()` creates a new chat session. The UI sends one message per click rather than maintaining a multi-turn conversation.

### Configuration files
- `requirements.txt` lists Gradio, the Google GenAI SDK, and `python-dotenv`.
- `.env.example` documents the environment variable name but contains no secret.
- `.gitignore` excludes `.env`, virtual environments, and generated runtime files.
- `LICENSE` contains the MIT license.
- `README.md` has installation steps and the screenshot.

## Why no database or login?
The stated prototype rules prohibit both. Listings are held in Gradio's per-session state, so they disappear when the session is reset and do not sync to another student's device. In a future version, shared persistence, school/community verification, reporting/moderation, and secure contact flows would need a separate design. Payments and message delivery are intentionally not implemented.

## AI-call rule
The page does not call Gemma when it loads, when someone searches, or when someone adds a listing. Only three explicit AI buttons call the model, and each button handler runs one model inference. The photo flow also uploads the image required by the API, but sends only one image-plus-prompt inference to Gemma.

## Technical note
Gemma's Gemini API usage follows Google's official guide: <https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api>.
