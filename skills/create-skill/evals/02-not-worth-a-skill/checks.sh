#!/usr/bin/env bash
# Clean case: no skill is created, and the answer says why not.
extra=$(ls skills | grep -v '^sample$' | head -1)
[ -z "$extra" ] || { echo "created skills/$extra"; exit 1; }
grep -qiE "not (worth|a good|needed|necessary)|does(n't| not) (need|deserve|warrant)|no skill|already know|base model|shouldn't (be )?(a )?skill|(not|n't|won't) (creat|writ|mak)|decline" "$EVAL_OUTPUT" || { echo "the answer does not decline or explain"; exit 1; }
