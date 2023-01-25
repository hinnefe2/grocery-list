const groceryListApp = () => ({
    ingredients: [],
    recipe_urls: [],
    setIngredients(ingredients) {
        this.ingredients = ingredients;
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
        // supress the submit so the the page does not refersh 
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
                    editing: false
                }
            ]);

            fetch(`https://faas.schollz.com/?import=github.com/schollz/ingredients&func=IngredientsFromURL(%22${recipe_url}%22)`)
                .then((response) => response.json())
                .then((data) => {
                    data.ingredients.map(i => { this.addIngredient(event, i, recipe_id) })
                });

            // reset the input field 
            this.$root.querySelector('.recipe_input').value = '';
        }
    },
    addIngredient(event, ingredient, recipe_id = -1) {
        // supress the submit so the the page does not refersh 
        event.preventDefault();

        if (ingredient) {
            const id = "id_" + Math.random().toString(16).slice(2)
            // use spread function to add new todo
            this.setIngredients([
                ...this.ingredients,
                {
                    id,
                    recipe_id: recipe_id,
                    item: `${ingredient.measure.amount} ${ingredient.measure.name} ${ingredient.name}`,
                    completed: false,
                    editing: false
                }
            ]);
        } else {
            // retrieve data directly from DOM with magic property root
            var ingredient = this.$root.querySelector('.ingredient_input').value;
            const id = "id_" + Math.random().toString(16).slice(2)

            // use spread function to add new todo
            this.setIngredients([
                ...this.ingredients,
                {
                    id,
                    recipe_id: recipe_id,
                    item: ingredient,
                    completed: false,
                    editing: false
                }
            ]);

            // reset the input field 
            this.$root.querySelector('.ingredient_input').value = '';
        }
    },
    removeIngredient(event, id) {
        // so supress the submit so the the page does not refersh 
        event.preventDefault();

        // we will use filter to remove todos based on id
        this.setIngredients(this.ingredients.filter((todo) => todo.id !== id));

        // this.saveState();
    },
    removeRecipe(event, recipe_id) {
        // so supress the submit so the the page does not refersh 
        event.preventDefault();

        // we will use filter to remove todos based on id
        this.setRecipeURLs(this.recipe_urls.filter((recipe) => recipe.recipe_id !== recipe_id));
        this.setIngredients(this.ingredients.filter((todo) => todo.recipe_id !== recipe_id));

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