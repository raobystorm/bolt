// Update with your config settings.

/**
 * @type { Object.<string, import("knex").Knex.Config> }
 */
module.exports = {
  production: {
    client: "mysql",
    connection: {
      host: "bolt-db.c3s9aj87pxhh.us-west-2.rds.amazonaws.com",
      user: "admin",
      password: "",
      database: "bolt",
    },
    pool: {
      min: 2,
      max: 10,
    },
    migrations: {
      tableName: "knex_migrations",
      directory: "./migrations",
    },
  },
};
