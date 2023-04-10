import * as knex from "knex";

export async function up(knex: knex.Knex): Promise<void> {
  return knex.schema
    .createTable("article", (table) => {
      table.bigIncrements("id").primary();
      table.string("title", 255).notNullable();
      table.string("author", 255).notNullable();
      table.string("org_url", 255).notNullable();
      table.string("text_path", 255);
      table.string("sumary_path", 255);
      table.string("image_path", 255);
      table.string("thumbnail_path", 255);
      table.bigint("source_id").unsigned().references("source.id");
      table.timestamp("created_at").defaultTo(knex.fn.now());
      table.timestamp("updated_at").defaultTo(knex.raw("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"));
    })
    .createTable("user", (table) => {
      table.bigIncrements("id").primary();
      table.string("lang", 255).notNullable();
      table.string("email", 255).notNullable();
      table.timestamp("created_at").defaultTo(knex.fn.now());
      table.timestamp("updated_at").defaultTo(knex.raw("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"));
    })
    .createTable("user_article", (table) => {
      table.bigIncrements("id").primary();
      table.bigint("user_id").unsigned().references("user.id");
      table.bigint("article_id").unsigned().references("article.id");
      table.bigint("rank");
      table.timestamp("created_at").defaultTo(knex.fn.now());
      table.timestamp("updated_at").defaultTo(knex.raw("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"));
    })
    .createTable("source", (table) => {
      table.bigIncrements("id").primary();
      table.string("name", 255).notNullable();
      table.string("base_url", 255).notNullable();
      table.string("rss_url", 255).notNullable();
      table.string("text_xpath", 255).notNullable();
      table.string("title_xpath", 255).notNullable();
      table.timestamp("created_at").defaultTo(knex.fn.now());
      table.timestamp("updated_at").defaultTo(knex.raw("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"));
    })
    .createTable("user_source", (table) => {
      table.bigIncrements("id").primary();
      table.integer("user_id").unsigned().references("user.id");
      table.integer("source_id").unsigned().references("source.id");
      table.timestamp("created_at").defaultTo(knex.fn.now());
      table.timestamp("updated_at").defaultTo(knex.raw("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"));
    })
    .createTable("category", (table) => {
      table.bigIncrements("id").primary();
      table.string("name", 255).notNullable();
      table.timestamp("created_at").defaultTo(knex.fn.now());
      table.timestamp("updated_at").defaultTo(knex.raw("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"));
    });
}

export async function down(knex: knex.Knex): Promise<void> {
  return knex.schema
    .dropTableIfExists("category")
    .dropTableIfExists("user_source")
    .dropTableIfExists("source")
    .dropTableIfExists("user_article")
    .dropTableIfExists("user")
    .dropTableIfExists("article");
}