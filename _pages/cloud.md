---
title: "CLOUD"
layout: default
permalink: /categories/cloud/
---

<div style="display:flex; justify-content:center; gap:1.5em; max-width:1400px; margin:0 auto; padding:2em;">
  <aside class="sidebar-ad sidebar-ad--left">
    <div style="position:sticky; top:5em;">
      <ins class="adsbygoogle"
           style="display:block"
           data-ad-client="ca-pub-7225106491387870"
           data-ad-slot="4201407843"
           data-ad-format="vertical"
           data-full-width-responsive="false"></ins>
      <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
    </div>
  </aside>

  <div class="content-container" style="flex:1; min-width:0;">
    <h1 class="category-page__title">CLOUD</h1>

    <div class="posts-grid">
      {% assign posts = site.categories["CLOUD"] %}
      {% for post in posts %}
        {% include archive-single.html type="card" %}
      {% endfor %}
    </div>
  </div>

  <aside class="sidebar-ad sidebar-ad--right">
    <div style="position:sticky; top:5em;">
      <ins class="adsbygoogle"
           style="display:block"
           data-ad-client="ca-pub-7225106491387870"
           data-ad-slot="4201407843"
           data-ad-format="vertical"
           data-full-width-responsive="false"></ins>
      <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
    </div>
  </aside>
</div>
