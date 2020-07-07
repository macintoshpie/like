<template>
  <div>
    <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
    <div v-if="infoMessage" class="info-message">{{ infoMessage }}</div>

    <div v-if="currentUser === null">
      <input v-model="signUpUsername" placeholder="username">
      <input v-model="signUpEmail" placeholder="email">
      <button v-on:click="signUp">sign up</button>
    </div>

    <div v-if="currentUser === null">
      <input v-model="loginEmail" placeholder="email">
      <button v-on:click="login">login</button>
    </div>
    
    <button v-on:click="logout" v-if="currentUser !== null">logout</button>

    <div v-if="currentUser !== null">
      <input v-model="postInput">
      <button v-on:click="submitPost">submit</button>
    </div>

    <div class='container'>
      <div v-for="post in posts" :key='post.id' class='feed-post'>
        <div class='user-link'>
          <a href="#" v-on:click='deletePost(post.id)' v-if='currentUser !== null && post.user_id === currentUser.id'>(x)</a>
          <a :href='"/api/users/" + post.user_id' v-if='currentUser === null || post.user_id !== currentUser.id'>{{ post.username }}</a>
          
        </div>
        <div class='post-link'>
          <a :href='post.uri'>{{ post.uri }}</a>
        </div>
      </div>
      <button v-on:click="fetchMorePosts" v-if='postsNextLink'>
        more
      </button>
    </div>
  </div>
</template>

<script>

export default {
  name: 'App',
  data: function() {
    return {
      postsNextLink: 'api/feed',
      posts: [],
      currentUser: null,
      loginEmail: '',
      signUpUsername: '',
      signUpEmail: '',
      postInput: '',
      errorMessage: '',
      infoMessage: '',
    }
  },
  mounted() {
    this.fetchMorePosts()
    this.fetchCurrentUser()
  },
  methods: {
    signUp: function() {
      fetch(
        `api/users/`,
        {
          method: 'POST',
          body: JSON.stringify({username: this.signUpUsername, email: this.signUpEmail})
        })
        .then(response => response.json())
        .then(response => {
          if ('error' in response) {
            console.log(response.error)
            this.errorMessage = response.error.message
            return
          }
          this.currentUser = response.data.items[0]
          this.infoMessage = 'Successfully created and logged into new account'
        })
    },
    login: function() {
      fetch(
        `api/login`,
        {
          method: 'POST',
          body: JSON.stringify({email: this.loginEmail})
        })
      .then(response => response.json())
      .then(response => {
        if ('error' in response) {
          this.errorMessage = response.error.message
          return
        }
        this.infoMessage = 'Check your email'
      })
    },
    logout: function() {
      console.log('hello')
      fetch(
        `api/users/${this.currentUser.id}/session`,
        {method: 'DELETE'})
        .then(response => response.json())
        .then(response => {
          if ('error' in response) {
            this.errorMessage = response.error.message
            return
          }
          this.currentUser = null
          this.infoMessage = 'Successfully logged out'
        })
    },
    fetchMorePosts: function() {
      if (this.postsNextLink == null) {
        return
      }
      fetch(this.postsNextLink)
        .then(response => response.json())
        .then(response => {
          this.posts = [...this.posts, ...response.data.items]
          this.postsNextLink = response.data.nextLink
        });
    },
    fetchCurrentUser: function() {
      if (this.currentUser !== null) {
        return
      }

      fetch('api/users/me')
        .then(response => response.json())
        .then(response => {
          if ('error' in response) {
            console.log('Failed to fetch user: ', response.error)
            this.errorMessage = response.error.message
            return
          }
          this.currentUser = response.data.items[0]
        })
    },
    deletePost: function(postId) {
      fetch(
        `api/users/${this.currentUser.id}/posts/${postId}`,
        {method: 'DELETE'})
        .then(response => response.json())
        .then(response => {
          if ('error' in response) {
            console.log(response.error)
            this.errorMessage = response.error.message
            return
          }
          const postIndex = this.posts.findIndex((post) => post.id === postId)
          if (postIndex >= 0) {
            this.posts.splice(postIndex, 1)
          }
          this.infoMessage = 'Deleted post'
        })
    },
    submitPost: function() {
        let urlRegex = /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)/
        const postInput = this.postInput
        if (urlRegex.test(postInput)) {
          fetch(
            `api/users/${this.currentUser.id}/posts/`,
            {
              method: 'POST',
              body: JSON.stringify({uri: postInput})
            })
            .then(response => response.json())
            .then(response => {
              if ('error' in response) {
                console.log(response.error)
                this.errorMessage = response.error.message
                return
              }
              this.posts = [
                response.data.items[0],
                ...this.posts
              ]
              this.infoMessage = 'Created post'
            })
        } else {
          this.errorMessage = 'Invalid url (must include http or https)'
        }
    }
  }
}
</script>

<style>
body {
  font-family:'Times New Roman', Times, serif
}

.container {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.feed-post {
  width: 500px;
  padding: 10px;
}

.post-link {
  font-size: 2rem;
  overflow-wrap: break-word;
}

.user-link>a {
  color: black;
  text-decoration: none;
}

.user-link>a:hover {
  text-decoration: underline;
}

.error-message {
  background-color: coral;
}

.info-message {
  background-color: cornflowerblue;
}
</style>
