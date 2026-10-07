# Campus Customs: Design Changes (Problem 10)

**Goal:** make the site feel like a real Yale storefront, not a homework app, so shoppers trust it, browse longer, and find the path to a product quickly. Only the frontend look changed: CSS, page markup, fonts, and favicon. Backend, database, agent, memory, tools, and login logic were not touched.

## Visual identity

| Change | Why it helps |
|---|---|
| **Yale Blue (#00356b) + deep navy + warm ivory background** instead of flat grey-white | Yale Blue is instantly recognizable to the audience. Ivory feels like a boutique shop rather than a dashboard, and makes white product photos stand out. |
| **Typography:** *Playfair Display* (collegiate serif) for headings and prices, *Inter* for body text | The serif signals heritage and quality, which matches licensed university apparel. Inter keeps small text (sizes, stock, forms) easy to read. |
| **Subtle diagonal "varsity stripe" texture** on the hero, page banners, and auth panel | Adds depth and a sporty feel without distracting from products |
| **CC monogram favicon and badge** (replacing the default Vite logo) | Looks like a real brand in the browser tab and header |

## Page by page

- **Header:**
  - White, frosted header that stays at the top while scrolling.
  - Animated underline on the current page.
  - "Create account" as a solid pill button.
  - Logged-in users see an initial avatar.
  - On phones it collapses into a **hamburger menu**.
  - *Why:* navigation is always one tap away, and the main account action stands out.
- **Home:**
  - Split hero: a big serif headline ("Wear your *Bulldog* blue.") beside a tilted **collage of three real hoodies** from the catalogue, one of them gently floating, with a price tag.
  - A **stats strip** using real data: 102 styles, 6 categories, XS–XXL, officially licensed.
  - Icon value cards, "Fan favorites", and a **gift promo band**.
  - *Why:* shoppers see actual products within a second, trust signals are up front, and there are three clear routes into the catalogue.
- **Products:**
  - Navy page banner with the **filter bar floating over it** as a white card: pill-shaped search and dropdowns, a live result count, and "Clear filters ✕".
  - Product cards have:
    - a soft gradient photo backdrop;
    - image zoom and lift on hover;
    - a "View details" pill that slides in;
    - an arrow button;
    - descriptions limited to two lines so rows stay even.
  - **Skeleton shimmer cards** while loading, and a friendly empty state with a clear-filters button.
  - Chat results get a more distinct "From your chat" banner.
  - *Why:* browsing feels fast and tidy, every card clearly looks clickable, and loading never shows a blank page.
- **Product detail:**
  - Breadcrumb (Home / Products / item).
  - Large framed image that stays in view while scrolling.
  - Large serif price with an **availability pill** ("In stock · 5 of 6 sizes").
  - **Color-coded size tiles:** navy = in stock, **amber = "Only N left"**, dashed and crossed out = sold out.
  - An assurance box: officially licensed, 57 Broadway, and "ask our assistant".
  - *Why:* the buying decision (price, size, availability) is visible at a glance, and low stock creates gentle urgency.
- **About:** banner, readable two-column story with a **pull quote**, and info cards (visit, what we carry, need a hand?) plus a "Explore the collection" button.
- **Log in / Create account:**
  - Split card with a navy **brand panel listing account benefits** (saved chat, personal help).
  - Larger inputs with focus rings and full-width buttons.
  - Clear green, red, and blue alerts.
  - *Why:* reminding people why to sign up should improve conversion, and the forms feel trustworthy.
- **Footer:**
  - A Yale Blue band with a playful tagline ("For God, for Country, and for Yale. And for your closet.") and a "Shop the collection" button.
  - Four tidy link columns.
  - *Why:* one last call to action before leaving the page.
- **Chat:**
  - "**Ask our assistant**" pill launcher with a soft pulse, which shrinks to an icon on phones.
  - Panel slides in, with a CC avatar and an "online" dot.
  - Chat-style bubbles with tails and **animated typing dots**.
  - A horizontally scrollable suggestion row and a rounded input.
  - *Why:* the assistant looks inviting and alive, so more shoppers try it, and the assistant leads straight to product cards.

## Motion and responsiveness

- Gentle **fade-up entrances** for pages and cards, hover lifts on cards and buttons, and the chat slide-in. All animations are turned off when the visitor has **reduced motion** switched on.
- Layout breakpoints:

| Width | Changes |
|---|---|
| ≤ 980 px | Hero, product detail, and About stack into one column |
| ≤ 820 px | Hamburger menu; auth card stacks |
| ≤ 640 px | 2-column product grid, compact cards, full-width filters, icon-only chat button |

- Checked at laptop width (~1280 px) and phone width (375 px): no sideways scrolling.

## Why this should help customers stay and buy

1. **Trust:** a polished, on-brand look plus "officially licensed" signals reassures shoppers that the gear is authentic.
2. **Faster product discovery:** real products in the hero, clear cards, filters that float in view, and skeleton loading reduce bounce.
3. **Clear calls to action:** solid pill buttons ("Shop the collection", "Create account", "Ask our assistant") stand out on every page.
4. **Confident size choice:** color-coded stock and the availability pill answer "can I get my size?" without hunting.
5. **Mobile-friendly:** many campus shoppers browse on phones, and the layout, menu, and chat all adapt.
