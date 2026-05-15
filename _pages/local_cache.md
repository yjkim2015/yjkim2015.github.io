---
title: "LOCAL_CACHE"
layout: default
permalink: /categories/local_cache/
---

<div class="content-container" style="max-width:1100px; margin:0 auto; padding:2em 1em;">
  <h1 class="category-page__title">LOCAL_CACHE</h1>

  <div class="posts-grid">
    {% assign posts = site.categories["LOCAL_CACHE"] %}
    {% for post in posts %}
      {% include archive-single.html type="card" %}
    {% endfor %}
  </div>
</div>
