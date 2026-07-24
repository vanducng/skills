# Type: er-diagram

## Purpose
Show entities and relationships in a relational schema. Audience: anyone reading a database design.

## When to use
Trigger words:
- "ER diagram", "schema", "tables", "entities"
- "one-to-many", "many-to-many", "foreign key", "relationship"
- mentions of database modeling

## Visual conventions
- Entities: rectangular box with header band (entity name in semibold) + body listing key columns; PK marked with `🔑`-glyph or "(pk)" suffix in monospace
- Relationships: line between entities, labeled with verb (e.g. "places", "owns"). Cardinality at each end (1, 0..1, *, 1..*)
- Weak entities: dashed outer border
- Inheritance: open triangle pointing to the parent
- Junction tables: explicit, drawn as a small entity with FKs to the two parents

## Layout direction
Cluster strongly-related entities. **Core entities** (most connections) sit centrally; dependent entities at edges. No mandatory direction; readability wins.

## Level of detail
Include: entity name, primary key, foreign keys, cardinality, relationship verb.
Exclude: full column lists unless prompt explicitly asks. Show 3–6 illustrative columns max per entity.

## Image-prompt template
```
ER diagram, flat vector, technical illustration aesthetic, calm and readable.

Entities (with primary key + 3-6 illustrative columns each): {entities}
Relationships (with cardinality on each end + verb label): {relationships}

Style: the surface background color, primary color entity borders and text, accent color on the {core entity} or none if no clear focal entity, muted color for relationship lines. 2px primary entity borders, 1.5px relationship lines.

Typography: sans-serif for entity names (semibold for header), monospace for column names. 14pt minimum.

Layout: cluster connected entities. Core entity centrally placed; satellites around it. Relationship lines never cross entity boxes. Cardinality notation (1, 0..1, *, 1..*) at each end. Labels above the relationship line, near the midpoint.

Do NOT invent entities or columns. Do NOT exceed 12 entities - split otherwise.
```

## SVG-prompt template
```
Output ONLY valid SVG 1.1 per the SVG contract. Use class .service for entity rectangles (with header strip + body), .connection-sync for relationship lines.

Entities: {entities}
Relationships: {relationships}

viewBox="0 0 1600 900". Each entity: 220px wide, header band fill #f1ede5, body list columns in monospace. Relationship lines as <path>. Cardinality endpoints as small <text>: "1", "0..1", "*", "1..*". Verb label as <text> near midpoint.
```

## Golden examples

### Example 1
**User input:** "users place orders, orders contain line items pointing to products"
**Refined image prompt (excerpt):**
> ER diagram. Entities:
> - User (id pk, email, name)
> - Order (id pk, user_id fk, total, created_at)
> - LineItem (id pk, order_id fk, product_id fk, qty, price)
> - Product (id pk, sku, name, price)
> Relationships: User --(1, *)-- "places" --(*, 1)-- Order; Order --(1, *)-- "contains" --(*, 1)-- LineItem; Product --(1, *)-- "referenced by" --(*, 1)-- LineItem.

### Example 2
**User input:** "blog: authors write posts, posts have tags (many-to-many), comments belong to posts"
**Refined image prompt (excerpt):**
> ER diagram. Author (id pk, name, email), Post (id pk, author_id fk, title, body, created_at), Tag (id pk, name), PostTag junction (post_id fk, tag_id fk), Comment (id pk, post_id fk, author_name, body). Author 1..* Post; Post *..* Tag via PostTag; Post 1..* Comment.

## Common mistakes to avoid
- Do NOT skip cardinality on relationships.
- Do NOT cross relationship lines when re-arranging entities fixes it.
- Do NOT list every column - pick the 3–6 most relevant.
- Do NOT use the success/error colors here.
