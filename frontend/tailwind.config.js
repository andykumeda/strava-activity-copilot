/** @type {import('tailwindcss').Config} */
export default {
    darkMode: 'class',
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            typography: ({ theme }) => ({
                DEFAULT: {
                    css: {
                        a: {
                            color: theme('colors.orange.600'),
                            textDecoration: 'underline',
                            fontWeight: '600',
                            '&:hover': {
                                color: theme('colors.orange.700'),
                            },
                        },
                    },
                },
                invert: {
                    css: {
                        a: {
                            color: theme('colors.orange.400'),
                            '&:hover': {
                                color: theme('colors.orange.300'),
                            },
                        },
                    },
                },
            }),
        },
    },
    plugins: [require('@tailwindcss/typography')],
}
