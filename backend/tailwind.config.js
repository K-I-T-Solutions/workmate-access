/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/static/index.html'],
  safelist: [
    // Brand-Klassen (dynamisch im JS aufgebaut)
    { pattern: /^(bg|text|ring|border|focus:ring|hover:bg)-brand(-dim|-light|-glow)?$/ },
    { pattern: /^bg-brand-(dim|light|glow)$/ },
    'hover:bg-brand-dim',
    // Dynamisch im JS generierte Layout-Klassen
    'grid-cols-1', 'grid-cols-2', 'grid-cols-3', 'grid-cols-4',
    'md:grid-cols-2', 'xl:grid-cols-3', 'lg:grid-cols-3',
    // Farben die per JS-Template-Literals zusammengebaut werden
    { pattern: /^(bg|text|border)-(slate|emerald|red|amber|violet|cyan|blue|green|yellow)-(50|100|200|300|400|500|600|700|800|900)$/ },
    { pattern: /^hover:(bg|text)-(slate|emerald|red|amber)-(50|100|600|700)$/ },
    // Utility-Klassen für Checkboxen
    'accent-cyan-500',
    // Responsive-Klassen aus der Tabellen-Grid-Definition
    'w-full', 'w-1\/2', 'w-1\/3', 'w-2\/3',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#00b8d4',
          dim:     '#0097b2',
          light:   '#e0feff',
          glow:    '#00e5ff',
        }
      }
    }
  },
  plugins: [],
}
