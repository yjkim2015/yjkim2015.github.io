---
title: "GIT"
layout: category-page
permalink: /categories/git/
---

<div class="content-container" style="max-width:1100px; margin:0 auto; padding:2em 1em;">
  <h1 class="category-page__title">GIT</h1>

  <div class="posts-grid">
    {% assign posts = site.categories["GIT"] %}
    {% for post in posts %}
      {% include archive-single.html type="card" %}
    {% endfor %}
  </div>
</div>
