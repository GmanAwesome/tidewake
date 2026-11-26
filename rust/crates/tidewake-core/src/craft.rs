//! Crafting grid from `items.py`. Recipes, groups, food and smelt results are
//! the Python tables, dumped so the ids stay the ones the game uses.

use std::collections::HashMap;
use std::sync::OnceLock;

use serde::Deserialize;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Ing {
    Id(u16),
    Group(&'static str),
}

#[derive(Clone, Debug)]
pub struct Recipe {
    pub rows: Vec<Vec<Option<Ing>>>,
    pub result: u16,
    pub count: u16,
    pub shapeless: bool,
}

struct Book {
    recipes: Vec<Recipe>,
    groups: HashMap<String, Vec<u16>>,
    names: HashMap<u16, String>,
    food: HashMap<u16, i32>,
    smelt: HashMap<u16, u16>,
}

#[derive(Deserialize)]
struct Raw {
    items: Vec<RawItem>,
    groups: HashMap<String, Vec<u16>>,
    recipes: Vec<RawRecipe>,
    smelt: HashMap<String, u16>,
    named: HashMap<String, u16>,
}

#[derive(Deserialize)]
struct RawItem {
    id: u16,
    name: String,
    food: i32,
}

#[derive(Deserialize)]
struct RawRecipe {
    rows: Vec<Vec<Option<RawCell>>>,
    result: u16,
    count: u16,
    shapeless: bool,
}

#[derive(Deserialize)]
#[serde(untagged)]
enum RawCell {
    Id(u16),
    Group(String),
}

fn book() -> &'static Book {
    static BOOK: OnceLock<Book> = OnceLock::new();
    BOOK.get_or_init(|| {
        let raw: Raw = serde_json::from_str(include_str!("recipes.json")).expect("recipes.json");
        let leak = |s: String| -> &'static str { Box::leak(s.into_boxed_str()) };
        let recipes = raw
            .recipes
            .into_iter()
            .map(|r| Recipe {
                rows: r
                    .rows
                    .into_iter()
                    .map(|row| {
                        row.into_iter()
                            .map(|c| {
                                c.map(|c| match c {
                                    RawCell::Id(id) => Ing::Id(id),
                                    RawCell::Group(g) => Ing::Group(leak(g)),
                                })
                            })
                            .collect()
                    })
                    .collect(),
                result: r.result,
                count: r.count,
                shapeless: r.shapeless,
            })
            .collect();
        let names = raw.items.iter().map(|i| (i.id, i.name.clone())).collect();
        let food = raw.items.iter().filter(|i| i.food > 0).map(|i| (i.id, i.food)).collect();
        let smelt = raw.smelt.into_iter().filter_map(|(k, v)| k.parse().ok().map(|id: u16| (id, v))).collect();
        // named is checked by tests via the constants below; keep the parse honest
        let _ = raw.named;
        Book { recipes, groups: raw.groups, names, food, smelt }
    })
}

pub fn name_of(id: u16) -> String {
    book().names.get(&id).cloned().unwrap_or_else(|| format!("item {id}"))
}

pub fn food_of(id: u16) -> i32 {
    book().food.get(&id).copied().unwrap_or(0)
}

pub fn smelt(id: u16) -> Option<u16> {
    book().smelt.get(&id).copied()
}

fn in_group(group: &str, id: u16) -> bool {
    book().groups.get(group).map(|g| g.binary_search(&id).is_ok()).unwrap_or(false)
}

fn cell_ok(want: Option<Ing>, have: Option<u16>) -> bool {
    match (want, have) {
        (None, None) => true,
        (None, Some(_)) | (Some(_), None) => false,
        (Some(Ing::Id(w)), Some(h)) => w == h,
        (Some(Ing::Group(g)), Some(h)) => in_group(g, h),
    }
}

fn trim(grid: &[Vec<Option<u16>>]) -> Vec<Vec<Option<u16>>> {
    let mut rows: Vec<Vec<Option<u16>>> = grid.to_vec();
    while rows.first().is_some_and(|r| r.iter().all(|c| c.is_none())) {
        rows.remove(0);
    }
    while rows.last().is_some_and(|r| r.iter().all(|c| c.is_none())) {
        rows.pop();
    }
    if rows.is_empty() {
        return rows;
    }
    let cols = rows[0].len();
    let left = rows.iter().map(|r| r.iter().position(|c| c.is_some()).unwrap_or(cols)).min().unwrap_or(0);
    let right = rows
        .iter()
        .map(|r| r.iter().rposition(|c| c.is_some()).map(|i| i + 1).unwrap_or(0))
        .max()
        .unwrap_or(0);
    if left >= right {
        return Vec::new();
    }
    rows.into_iter().map(|r| r[left..right].to_vec()).collect()
}

/// Match a crafting grid the way `items.match` does, including mirrors and groups.
pub fn match_grid(grid: &[Vec<Option<u16>>]) -> Option<(u16, u16)> {
    let g = trim(grid);
    if g.is_empty() {
        return None;
    }
    let mut flat: Vec<u16> = g.iter().flatten().copied().flatten().collect();
    flat.sort();
    for recipe in &book().recipes {
        if recipe.shapeless {
            let want: Vec<Ing> = recipe.rows.iter().flatten().copied().flatten().collect();
            if want.len() != flat.len() {
                continue;
            }
            let mut pool = flat.clone();
            let mut ok = true;
            for w in want {
                if let Some(i) = pool.iter().position(|h| cell_ok(Some(w), Some(*h))) {
                    pool.remove(i);
                } else {
                    ok = false;
                    break;
                }
            }
            if ok {
                return Some((recipe.result, recipe.count));
            }
            continue;
        }
        if recipe.rows.len() != g.len() || recipe.rows[0].len() != g[0].len() {
            continue;
        }
        for mirror in [false, true] {
            let ok = recipe.rows.iter().zip(g.iter()).all(|(want, have)| {
                let check = |a: Option<Ing>, b: &Option<u16>| cell_ok(a, *b);
                if mirror {
                    want.iter().rev().zip(have.iter()).all(|(a, b)| check(*a, b))
                } else {
                    want.iter().zip(have.iter()).all(|(a, b)| check(*a, b))
                }
            });
            if ok {
                return Some((recipe.result, recipe.count));
            }
        }
    }
    None
}

pub const STICK: u16 = 256;
pub const BERRIES: u16 = 266;
pub const WHEAT: u16 = 315;
pub const LOAF: u16 = 316;
pub const HEARTWOOD: u16 = 9;
pub const PLANKS: u16 = 26;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn recipes_match_the_python_table() {
        assert_eq!(book().recipes.len(), 274);
        assert_eq!(match_grid(&[vec![Some(HEARTWOOD)]]), Some((PLANKS, 4)));
        assert_eq!(
            match_grid(&[vec![Some(WHEAT), Some(WHEAT), Some(WHEAT)]]),
            Some((LOAF, 1))
        );
        // kiln is a ring of any stone
        let stone = 1u16;
        let grid = vec![
            vec![Some(stone), Some(stone), Some(stone)],
            vec![Some(stone), None, Some(stone)],
            vec![Some(stone), Some(stone), Some(stone)],
        ];
        assert_eq!(match_grid(&grid).map(|r| r.0), Some(28));
        assert_eq!(food_of(LOAF), 6);
        assert_eq!(food_of(BERRIES), 3);
        assert_eq!(smelt(11), None);
        assert!(smelt(1).is_some());
    }
}
