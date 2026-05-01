---
title: "AI"
layout: default
permalink: /categories/ai/
---

<div class="main-container">
  <div class="content-container">
    <h1 class="category-page__title">AI</h1>

    {% assign posts = site.categories["AI"] %}
    {% for post in posts %}
      {% include archive-single.html %}
    {% endfor %}
  </div>
</div>
