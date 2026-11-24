const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '../../grocerylist.js'), 'utf8');

function createApp({ search = '', ingredients = {} } = {}) {
    const location = {
        hostname: 'localhost', protocol: 'http:', host: 'localhost',
        pathname: '/', search,
    };
    const window = {
        location,
        history: {
            pushState(state, title, url) {
                location.search = new URL(url).search;
            },
        },
    };
    const context = vm.createContext({
        location, window, btoa, atob, URLSearchParams,
        fetch: async () => ({ json: async () => ({ ingredients }) }),
    });
    vm.runInContext(source, context);
    const app = vm.runInContext('groceryListApp()', context);
    return { app, location };
}

const event = { preventDefault() {} };
const namesIn = (app) => Object.values(app.ingredients).flat().map((item) => item.item);

test('recipe import continues past pig’s feet and saves the chiles and finished state', async () => {
    // Preserve API section order: the original btoa error stopped the import in
    // section 1, after produce and pork shoulder but before the spices section.
    const ingredients = {
        0: [{ name: '1 whole white onion' }],
        1: [
            { name: '3 pounds boneless pork shoulder' },
            { name: '1 pound pig’s feet (optional)' },
        ],
        4: [{ name: 'Tostadas or chicharrón' }],
        6: [
            { name: '5 guajillo chiles, stems and seeds removed' },
            { name: '4 California chiles, stems and seeds removed' },
            { name: '2 ancho chiles, stems and seeds removed' },
        ],
    };
    const { app, location } = createApp({ ingredients });
    app.$root = {
        querySelector: () => ({ value: 'https://example.com/pozole' }),
    };
    app.addRecipe(event);
    await new Promise(setImmediate);

    assert.equal(namesIn(app).length, 7);
    assert.equal(app.recipe_urls[0].loading, false);
    const restored = createApp({ search: location.search }).app;
    restored.loadState();
    assert.equal(namesIn(restored).length, 7);
    assert.equal(restored.recipe_urls[0].loading, false);
    for (const item of Object.values(ingredients).flat()) {
        assert.ok(namesIn(restored).includes(item.name), item.name);
    }
});

test('shared links round-trip Unicode ingredient names and recipe URLs', () => {
    const { app, location } = createApp();
    const names = ['pig’s feet', 'chicharrón', '青椒', '🌶️ pepper', 'crème fraîche'];
    const recipeUrl = 'https://example.com/receta/青椒';
    app.setRecipeURLs([{ item: recipeUrl, loading: false }]);
    for (const name of names) {
        app.addIngredient(event, 0, { name });
    }
    const restored = createApp({ search: location.search }).app;
    restored.loadState();
    assert.deepEqual([...namesIn(restored)].sort(), names.sort());
    assert.equal(restored.recipe_urls[0].item, recipeUrl);
});

test('existing Latin-1 shared links remain readable, including raw base64 plus signs', () => {
    const state = {
        ingredients: { 0: [{ item: '~~~~~~' }, { item: 'jalapeño' }] },
        recipe_urls: [{ item: 'https://example.com/recipe', loading: true }],
    };
    const encoded = btoa(JSON.stringify(state));
    assert.ok(encoded.includes('+'), 'fixture must exercise raw base64 plus signs');
    const { app } = createApp({ search: '?q=' + encoded });
    app.loadState();
    assert.deepEqual(JSON.parse(JSON.stringify({
        ingredients: app.ingredients, recipe_urls: app.recipe_urls,
    })), state);
});
