// Mock answers in the shape the UI reads (see ../../../DATA.md).
// All values, sections and pages are copied from the PUDU manuals (English versions).

const PUDU = 'PUDU manuals'

// ---------- Technical question: BellaBot charging (screens 01.5, 02, 03a, 04a, 04b) ----------
const bellabotPower = [
  'Always use the original rechargeable batteries and chargers. Do not charge your robot using non-original chargers. If the charger is damaged, replace it immediately.',
  'When the battery drops to 20%, the robot should be charged timely. Running at a low battery for a long time may impair battery life.',
  'Make sure that the power voltage matches the voltage indicated on the charger, or it may cause damages to the charger.',
  'When using the charger, ensure that the fastener of the charging interface is fully engaged to avoid overheating during charging, which may cause burns or damage to the equipment.',
]

export const SPEC = {
  id: 'spec',
  question: 'How long does BellaBot charge, and what does it cost?',
  progress: [
    { step: 'search', detail: 'Now reading: BellaBot User Manual' },
    { step: 'search', detail: 'Now reading: BellaBot Pro User Manual' },
  ],
  searchedDetail: '2 match your question: BellaBot and BellaBot Pro',
  clarification: {
    question: 'Which BellaBot do you mean?',
    reason: 'Charging time and battery life differ between the two models.',
    options: [
      { label: 'BellaBot', detail: 'BellaBot User Manual' },
      { label: 'BellaBot Pro', detail: 'BellaBot Pro User Manual' },
      { label: 'Compare both', detail: 'Side by side, each value with its source' },
    ],
  },
  answer: {
    style: 'technical',
    meta: 'Answer for BellaBot · from 4 pages of the BellaBot User Manual',
    short_answer: {
      values: [
        { value: '4.5', unit: 'h', label: 'Full charge', n: 1 },
        { value: '12–24', unit: 'h', label: 'Battery life on a full charge', n: 1 },
      ],
    },
    text:
      'A full charge takes 4.5 hours, and the 25.6 Ah battery then keeps BellaBot running for 12 to 24 hours. [1] ' +
      'Plug it in when the battery drops to 20%: running low for long periods shortens battery life. [2] ' +
      'Use only the original charger, and make sure the charging connector is fully engaged so it doesn’t overheat. [2]' +
      '\n\n' +
      'If it won’t charge, open the rear cover of the battery box and check that the battery is seated and the key switch is set to ON. [3] ' +
      'To see how much charge is left, press the button on the battery: its indicator shows the level by color. [4]',
    // snapshot lines each claim cites, keyed "claimIndex:sourceNumber" (the backend may send `cited_lines`)
    claim_lines: { '0:1': [3, 4, 5], '1:2': [1], '2:2': [0, 3], '3:3': [0, 1], '4:4': [0, 2] },
    gaps: [{ topic: 'Price', text: 'I couldn’t verify the price: none of the 22 manuals lists prices or availability.' }],
    citations: [
      {
        n: 1, product_name: 'BellaBot', document: 'BellaBot User Manual', lang: 'en', family: 'Robots',
        section_path: '2. Product components › 2.4 Specifications', section_title: '2.4 Specifications',
        page: 3, pdf_page: 4, page_side: 'left', line: 'Table rows 4–6 of 10',
        pdf_file: 'BellaBot_User_Manual-multilanguage.pdf', pdf_url: '#',
        snapshot: { kind: 'table', heading: '2.4 Specifications', height: 344, cut: true,
          lines: [['Operating voltage', 'DC 23–29.4 V'], ['Power input', 'AC 100–240 V, 50/60 Hz'], ['Power output', '29.4 V/8 A'],
                  ['Battery capacity', '25.6 Ah'], ['Charging time', '4.5 h'], ['Battery life', '12–24 h'],
                  ['Cruise speed', '0.2–1.2 m/s (adjustable)'], ['Min. travel width', '70 cm']] },
        note: 'The specification table lists the charging time (4.5 h), the battery life (12–24 h) and the battery capacity (25.6 Ah). The answer joins the three values in one sentence and copies the numbers as printed.',
      },
      {
        n: 2, product_name: 'BellaBot', document: 'BellaBot User Manual', lang: 'en', family: 'Robots',
        section_path: '1. Safety instructions › 1.1 Power usage', section_title: '1.1 Power usage',
        page: 1, pdf_page: 3, page_side: 'left', line: 'Bullet 2 of 4',
        pdf_file: 'BellaBot_User_Manual-multilanguage.pdf', pdf_url: '#',
        snapshot: { kind: 'bullets', heading: '1.1 Power usage', height: 344, cut: true, lines: bellabotPower },
        note: 'The manual says the robot “should be charged timely” at 20%: the answer turns this into a direct instruction, “plug it in”. The manual says running low “may impair battery life”; the answer says “shortens”, which is stronger. The manual only says it can happen.',
      },
      {
        n: 3, product_name: 'BellaBot', document: 'BellaBot User Manual', lang: 'en', family: 'Robots',
        section_path: '4. Troubleshooting › 4.3 Charging failure', section_title: '4.3 Charging failure',
        page: 5, pdf_page: 5, page_side: 'left', line: 'Solution, bullets 1–2 of 4',
        pdf_file: 'BellaBot_User_Manual-multilanguage.pdf', pdf_url: '#',
        snapshot: { kind: 'bullets', heading: '4.3 Charging Failure', subheading: 'Solution', height: 236, cut: true,
          lines: [
            'Open the rear cover of the battery box and check if the battery is installed properly.',
            'Open the rear cover of the battery box and check if the key switch is turned to ON.',
            'Check if the rear cover of the battery box is installed properly.',
            'Check if the charger indicator is on. If not, the charging failure may be caused by a damaged charger. Please contact our technical engineers in time.',
          ] },
        figures: [{ url: '/figures/bellabot-en-p004R-fig02.png', width: 232, height: 141, page: 4,
          caption: 'Key switch location · 3. How to use, page 4' }],
        note: 'The manual lists four checks for a charging failure; the answer joins the two inside the battery box and says “seated” for “installed properly”. The figure comes from page 4 and shows where the key switch is.',
      },
      {
        n: 4, product_name: 'BellaBot', document: 'BellaBot User Manual', lang: 'en', family: 'Robots',
        section_path: '4. Troubleshooting › 4.4 Power-on failure', section_title: '4.4 Power-on failure',
        page: 6, pdf_page: 5, page_side: 'right', line: 'Solution, steps 1–2',
        pdf_file: 'BellaBot_User_Manual-multilanguage.pdf', pdf_url: '#',
        snapshot: { kind: 'bullets', heading: '4.4 Power-on Failure', subheading: 'Solution', height: 260, cut: true,
          lines: [
            'If the battery is low, please charge the robot. To check the battery level, proceed as follows:',
            '1. Open the rear cover of the battery box.',
            '2. Press the button on the battery to check the battery level.',
          ] },
        note: 'The manual explains how to check the battery level in two steps. The answer keeps the action, “press the button on the battery”, and says the indicator shows the level by color, as in the manual’s table.',
      },
    ],
  },
}

// ---------- Non-technical question: robot for 60 cm aisles (screen 03c) ----------
const spec = (rows) => rows

export const RECO = {
  id: 'reco',
  question: 'Which robot fits 60 cm aisles?',
  progress: [
    { step: 'search', detail: 'Now reading: KettyBot User Manual' },
    { step: 'search', detail: 'Now reading: BellaBot Pro User Manual' },
  ],
  answer: {
    style: 'plain',
    meta: 'Plain answer · 4 delivery robots compared · from 4 manuals',
    short_answer: {
      headline: 'KettyBot or KettyBot Pro',
      text: 'Both pass through aisles as narrow as 55 cm, so 60 cm is enough. [1][2]',
    },
    text:
      'BellaBot Pro needs at least 65 cm and BellaBot 70 cm, so neither fits your aisles. [3][4] ' +
      'Between the two KettyBots, the Pro runs longer on one charge: 11 hours without load, against more than 8 hours. [2][1]',
    claim_lines: { '0:3': [5], '0:4': [5], '1:2': [3], '1:1': [3] },
    gaps: [],
    comparison: {
      products: [
        { id: 'kettybot', name: 'KettyBot', n: 1 },
        { id: 'kettybot-pro', name: 'KettyBot Pro', n: 2 },
        { id: 'bellabot-pro', name: 'BellaBot Pro', n: 3 },
        { id: 'bellabot', name: 'BellaBot', n: 4 },
      ],
      recommended: ['kettybot', 'kettybot-pro'],
      rows: [
        { label: 'Fits 60 cm aisles', kind: 'fit', values: { 'kettybot': true, 'kettybot-pro': true, 'bellabot-pro': false, 'bellabot': false } },
        { label: 'Narrowest aisle', values: { 'kettybot': '55 cm', 'kettybot-pro': '55 cm', 'bellabot-pro': '65 cm', 'bellabot': '70 cm' } },
        { label: 'Runs on one charge', values: { 'kettybot': '> 8 h', 'kettybot-pro': '11 h (no-load operation)', 'bellabot-pro': '11 h (unloaded)', 'bellabot': '12–24 h' } },
        { label: 'Time to charge', values: { 'kettybot': '4 h', 'kettybot-pro': '4 h', 'bellabot-pro': '4.5 h', 'bellabot': '4.5 h' } },
        { label: 'Trays', values: { 'kettybot': 'Two trays and one dish-return box', 'kettybot-pro': 'Two trays and one dish-return box', 'bellabot-pro': 'Four', 'bellabot': 'Four' } },
        { label: 'Load per tray', values: { 'kettybot': '10 kg/layer', 'kettybot-pro': '10 kg/layer', 'bellabot-pro': '10 kg/layer', 'bellabot': '10 kg/layer' } },
      ],
    },
    citations: [
      { n: 1, product_name: 'KettyBot', document: 'KettyBot User Manual V1.0', lang: 'en', family: 'Robots',
        section_path: '2. Product components › 2.4 Specifications', section_title: '2.4 Specifications', page: 3, pdf_page: 4, page_side: 'left',
        pdf_file: 'KettyBot_User_Manual_V1.0.pdf', pdf_url: '#',
        snapshot: { kind: 'table', heading: '2.4 Specifications', height: 344, cut: true,
          lines: spec([['Battery capacity', '20 Ah'], ['Charging time', '4 h'], ['Charging mode', 'Manual and auto charging'], ['Battery life', '> 8 h'], ['Cruise speed', '0.5–1.2 m/s (adjustable)'], ['Navigation', 'Laser and visual integrated SLAM positioning'], ['Min. travel width', '55 cm'], ['Max. surmountable height', '5 mm']]) },
        note: 'The specification table gives a minimal travel width of 55 cm, so a 60 cm aisle is wide enough. The answer says it in plain words; the value is copied as printed.' },
      { n: 2, product_name: 'KettyBot Pro', document: 'KettyBot Pro User Manual V3.0', lang: 'en', family: 'Robots',
        section_path: '2. Product components › 2.4 Specifications', section_title: '2.4 Specifications', page: 3, pdf_page: 5, page_side: 'left',
        pdf_file: 'KettyBot_Pro_User_Manual_V3.0-multilanguage.pdf', pdf_url: '#',
        snapshot: { kind: 'table', heading: '2.4 Specifications', height: 344, cut: true,
          lines: spec([['Battery capacity', '25 Ah'], ['Charging time', '4 h'], ['Charging mode', 'Manual and auto charging'], ['Battery life', '11 h (no-load operation)'], ['Cruise speed', '0.2–1.2 m/s (adjustable)'], ['Navigation', 'Laser and visual integrated SLAM positioning'], ['Min. travel width', '55 cm'], ['Max. surmountable height', '5 mm']]) },
        note: 'Same minimal travel width as KettyBot, 55 cm. The answer calls the battery life of 11 h “without load” because the manual says “no-load operation”.' },
      { n: 3, product_name: 'BellaBot Pro', document: 'BellaBot Pro User Manual', lang: 'en', family: 'Robots',
        section_path: '2. Product components › 2.4 Specifications', section_title: '2.4 Specifications', page: 3, pdf_page: 4, page_side: 'left',
        pdf_file: 'BellaBot_Pro_User_Manual-multilanguage.pdf', pdf_url: '#',
        snapshot: { kind: 'table', heading: '2.4 Specifications', height: 344, cut: true,
          lines: spec([['Battery capacity', '25.6 Ah'], ['Charging time', '4.5 h'], ['Battery life', '11 h (unloaded)'], ['Cruise speed', '0.2–1.2 m/s (adjustable)'], ['Navigation', 'Visual positioning'], ['Min. travel width', '65 cm'], ['Max. surmountable height', '10 mm'], ['Max. climbing angle', '5°']]) },
        note: 'The minimal travel width is 65 cm, wider than the 60 cm aisles, so the answer says BellaBot Pro does not fit.' },
      { n: 4, product_name: 'BellaBot', document: 'BellaBot User Manual', lang: 'en', family: 'Robots',
        section_path: '2. Product components › 2.4 Specifications', section_title: '2.4 Specifications', page: 3, pdf_page: 4, page_side: 'left',
        pdf_file: 'BellaBot_User_Manual-multilanguage.pdf', pdf_url: '#',
        snapshot: { kind: 'table', heading: '2.4 Specifications', height: 344, cut: true,
          lines: spec([['Battery capacity', '25.6 Ah'], ['Charging time', '4.5 h'], ['Battery life', '12–24 h'], ['Cruise speed', '0.2–1.2 m/s (adjustable)'], ['Navigation', 'Laser and visual integrated SLAM positioning'], ['Min. travel width', '70 cm'], ['Max. surmountable height', '10 mm']]) },
        note: 'The minimal travel width is 70 cm, wider than the 60 cm aisles, so the answer says BellaBot does not fit.' },
    ],
  },
}

export function pickScenario(question) {
  const q = question.toLowerCase()
  if (/(fit|which robot|aisle|difference|compare|what changes|recommend)/.test(q)) return RECO
  return SPEC
}

export const COUNTS = '22 manuals · 13 robots and 9 accessories'
export const RESOURCE_ROOT = PUDU
