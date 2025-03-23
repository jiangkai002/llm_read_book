<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import HelloWorld from './components/HelloWorld.vue'
import Test from './components/Test.vue'
import PdfViewer from '@/components/PdfViewer.vue' // 导入
import ScreenCapture from '@/components/ScreenCapture.vue' // 导入
import { defineComponent } from 'vue'
</script>

<template>
  <div class="app">
    <PdfViewer url="/test.pdf" id="pdf" />
    <ScreenCapture targetId="pdf"  />
  </div>
</template>

<style scoped>
/* header {
  line-height: 1.5;
  max-height: 100vh;
} */

.app {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  width: 100%;
  background-color: brown;
}

.pdf-container {
  display: flex;
  flex-direction: column;
  align-items: left;
  padding: 0 var(--section-gap);
  max-width: 100%;
  overflow: hidden;
}

.logo {
  display: block;
  margin: 0 auto 2rem;
}

nav {
  width: 100%;
  font-size: 12px;
  text-align: center;
  margin-top: 2rem;
}

nav a.router-link-exact-active {
  color: var(--color-text);
}

nav a.router-link-exact-active:hover {
  background-color: transparent;
}

nav a {
  display: inline-block;
  padding: 0 1rem;
  border-left: 1px solid var(--color-border);
}

nav a:first-of-type {
  border: 0;
}

@media (min-width: 1024px) {
  header {
    display: flex;
    place-items: center;
    padding-right: calc(var(--section-gap) / 2);
  }

  .logo {
    margin: 0 2rem 0 0;
  }

  header .wrapper {
    display: flex;
    place-items: flex-start;
    flex-wrap: wrap;
  }

  nav {
    text-align: left;
    margin-left: -1rem;
    font-size: 1rem;

    padding: 1rem 0;
    margin-top: 1rem;
  }
}
</style>
