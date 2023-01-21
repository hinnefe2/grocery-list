const groceryListApp = () => ({
    ingredients: [],
    recipe_urls: [],
    addRecipe(event) {
        // supress the submit so the the page does not refersh 
        event.preventDefault();

        // retrieve data directly from DOM with magic property root
        var recipe_url = this.$root.querySelector('.recipe_input').value;

        if (recipe_url) {
            const recipe_id = "id_" + Math.random().toString(16).slice(2)
            // use spread function to add the new recipe url
            this.recipe_urls = [
                ...this.recipe_urls,
                {
                    recipe_id,
                    item: recipe_url,
                    completed: false,
                    editing: false
                }
            ];

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
            this.ingredients = [
                ...this.ingredients,
                {
                    id,
                    recipe_id: recipe_id,
                    item: `${ingredient.measure.amount} ${ingredient.measure.name} ${ingredient.name}`,
                    completed: false,
                    editing: false
                }
            ];
        } else {
            // retrieve data directly from DOM with magic property root
            var ingredient = this.$root.querySelector('.ingredient_input').value;
            const id = "id_" + Math.random().toString(16).slice(2)

            // use spread function to add new todo
            this.ingredients = [
                ...this.ingredients,
                {
                    id,
                    recipe_id: recipe_id,
                    item: ingredient,
                    completed: false,
                    editing: false
                }
            ];

            // reset the input field 
            this.$root.querySelector('.ingredient_input').value = '';
        }
    },
    remove_task(event, id) {
        // so supress the submit so the the page does not refersh 
        event.preventDefault();

        // we will use filter to remove todos based on id
        this.ingredients = this.ingredients.filter((todo) => todo.id !== id);
    },
    removeRecipe(event, recipe_id) {
        // so supress the submit so the the page does not refersh 
        event.preventDefault();

        // we will use filter to remove todos based on id
        this.recipe_urls = this.recipe_urls.filter((recipe) => recipe.recipe_id !== recipe_id);
        this.ingredients = this.ingredients.filter((todo) => todo.recipe_id !== recipe_id);
    },
    setEdit(task) {
        // set edit state to true
        task.editing = true;

        // focus the input field when user click on the task
        this.$root.querySelector('#task_edit-' + (task.id).toString()).focus();
    },
    completeTodo(task) {
        task.completed = !task.completed;
    }
});