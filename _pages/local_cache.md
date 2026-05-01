---
title: "LOCAL_CACHE"
layout: default
permalink: /categories/local_cache/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">LOCAL_CACHE</h1>

    {% assign posts = site.categories["LOCAL_CACHE"] %}
    {% for post in posts %}
      {% include archive-single.html %}
    {% endfor %}
  </div>
</div>
