<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import Test from './components/Test.vue'
import PdfViewer from '@/components/PdfViewer.vue' // 导入
import ScreenCapture from '@/components/ScreenCapture.vue' // 导入
import { defineComponent } from 'vue'
</script>

<template>
  <div class="app">
    <div class="pdf">
      <PdfViewer url="/test.pdf" id="pdf" />
    </div>
    <div class="right-container">
      <div class="block-2">
        <ScreenCapture targetId="pdf" />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* header {
  line-height: 1.5;
  max-height: 100vh;
} */

.app {
  display: flex;
  height: 100vh; /* 占满整个视口高度 */
  width: 100vw; /* 占满整个视口宽度 */
}

.pdf {
  width: 50%; /* 左侧占50%宽度 */
  height: 100%; /* 高度占满 */
  background-color: #f0f0f0; /* 可选：添加背景色以区分区域 */
}

.right-container {
  width: 50%; /* 右侧占50%宽度 */
  height: 100%; /* 高度占满 */
  display: flex;
  flex-direction: column; /* 垂直排列 Block 2 和 Block 3 */
}

.block-2 {
  height: 100vh; /* 占右侧高度的50% */
  background-color: #e0e0e0; /* 可选：添加背景色以区分区域 */
}

.block-3 {
  height: 50%; /* 占右侧高度的50% */
  background-color: #d0d0d0; /* 可选：添加背景色以区分区域 */
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
