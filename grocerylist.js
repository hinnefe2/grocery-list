const groceryListApp = () => ({
    _api_url: 'grocery-list-5ybpug4gia-uc.a.run.app',
    _api_warmup: fetch(`https://grocery-list-5ybpug4gia-uc.a.run.app`).then((response) => {}),
    // keys here must match the grocery store section ids returned by the API
    ingredients: {
        "0": [],
        "1": [],
        "2": [],
        "3": [],
        "4": [],
        "5": [],
        "6": [],
        "7": [],
        "8": [],
        "9": [],
    },
    recipe_urls: [],
    setIngredients(section, ingredients) {
        this.ingredients[section] = ingredients;
        this.saveState();
    },
    setRecipeURLs(recipe_urls) {
        this.recipe_urls = recipe_urls;
        this.saveState();
    },
    saveState() {
        var base_url = location.protocol + '//' + location.host + location.pathname;
        var encoded = btoa(JSON.stringify({ "ingredients": this.ingredients, "recipe_urls": this.recipe_urls }))
        window.history.pushState({}, "", base_url + "?q=" + encoded);
    },
    loadState() {
        var q_param = new URLSearchParams(location.search).get('q');

        if (q_param) {
            var decoded = JSON.parse(atob(q_param));
            this.recipe_urls = decoded["recipe_urls"];
            this.ingredients = decoded["ingredients"];
        };
    },
    addRecipe(event) {
        // suppress the submit so the the page does not refresh
        event.preventDefault();

        // retrieve data directly from DOM with magic property root
        var recipe_url = this.$root.querySelector('.recipe_input').value;

        if (recipe_url) {

            const recipe_id = "id_" + Math.random().toString(16).slice(2)
            // use spread function to add the new recipe url
            this.setRecipeURLs([
                ...this.recipe_urls,
                {
                    recipe_id,
                    item: recipe_url,
                    completed: false,
                    editing: false,
                    loading: true
                }
            ]);

            fetch(`https://${this._api_url}?recipe_url=${recipe_url}`)
                .then((response) => response.json())
                .then((data) => {
                    Object.entries(data.ingredients).forEach(([section, ingredient_list]) => {
                      ingredient_list.map(i => {
                        this.addIngredient(event, section, i, recipe_id) })
                    })
                }).finally((_) => {
                    this.recipe_urls.find((recipe) => recipe.recipe_id == recipe_id).loading = false
                });

            // reset the input field
            this.$root.querySelector('.recipe_input').value = '';

        }

    },
    addIngredient(event, section, ingredient, recipe_id = -1) {
        // suppress the submit so the the page does not refresh
        event.preventDefault();

        if (ingredient) {
            const id = "id_" + Math.random().toString(16).slice(2)
            // use spread function to add new todo
            this.setIngredients(section,
                [
                ...this.ingredients[section],
                {
                    id,
                    recipe_id: recipe_id,
                    item: ingredient.name,
                    completed: false,
                    editing: false
                }
            ]);
        } else {
            // retrieve data directly from DOM with magic property root
            var section = '9';
            var ingredient_name = this.$root.querySelector('.ingredient_input').value;
            const id = "id_" + Math.random().toString(16).slice(2)

            // use spread function to add new todo
            this.setIngredients(section,
                [
                ...this.ingredients[section],
                {
                    id,
                    recipe_id: recipe_id,
                    item: ingredient_name,
                    completed: false,
                    editing: false
                }
            ]);

            // reset the input field
            this.$root.querySelector('.ingredient_input').value = '';
        }
    },
    removeIngredient(event, id) {
        // so suppress the submit so the the page does not refresh
        event.preventDefault();

        // we will use filter to remove todos based on id
        Object.entries(this.ingredients).forEach(([section, ingredient_list]) => {
            this.setIngredients(section, ingredient_list.filter((todo) => todo.id !== id))
        });

        // this.saveState();
    },
    removeRecipe(event, recipe_id) {
        // so suppress the submit so the the page does not refresh
        event.preventDefault();

        // we will use filter to remove todos based on id
        this.setRecipeURLs(this.recipe_urls.filter((recipe) => recipe.recipe_id !== recipe_id));
        Object.entries(this.ingredients).forEach(([section, ingredient_list]) => {
            this.setIngredients(section, ingredient_list.filter((todo) => todo.recipe_id !== recipe_id))
        });

        // this.saveState();
    },
    setEdit(task) {
        // set edit state to true
        task.editing = true;

        // focus the input field when user click on the task
        this.$root.querySelector('#task_edit-' + (task.id).toString()).focus();
    },
    completeTodo(task) {
        task.completed = !task.completed;
    },
    mobileShare(event) {
        if (navigator.share) {
            navigator.share({
                title: 'Grocery List',
                text: "Here's a grocery list",
                url: window.location.href,
              })
              .then(() => console.log('Successful share'))
              .catch((error) => console.log('Error sharing', error));
          } else {
            this.$root.querySelector('#share-url').value = window.location.href;
            var shareModal = new bootstrap.Modal(document.getElementById('shareModal'), {});
            shareModal.show()
          }
    }

});
