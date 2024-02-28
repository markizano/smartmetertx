#!/usr/bin/mongo

// @eslint-disable-next-line no-undef
use smartmetertx;

pipeline = [{
    "$project": {
        "adjustedMonth": {
            "$subtract": [{
                "$month": "$datetime"
            }, {
                "$cond": [{
                    "$gte": [{
                        "$dayOfMonth": "$datetime"
                    }, 11]
                }, 1, 0]
            }]
        },
        "reading": 1,
        "startreading": 1,
        "endreading": 1,
        "datetime": 1
    }
}, {
    "$group": {
        "_id": "$adjustedMonth",
        "readingSum": {
            "$sum": "$reading"
        },
        "deltaSum": {
            "$sum": {
                "$subtract": ["$endreading", "$startreading"]
            }
        },
        "datetime": {
            "$first": "$datetime"
        }
    }
}, {
    "$project": {
        "_id": 0,
        "Month": {
            "$dateToString": {
                "format": "%Y-%m",
                "date": {
                    "$dateFromParts": {
                        "year": {
                            "$year": "$datetime"
                        },
                        "month": {
                            "$add": ["$_id", 1]
                        },
                        "day": 1
                    }
                }
            }
        },
        "readingSum": 1,
        "deltaSum": 1
    }
}, {
    "$sort": {
        "Month": 1
    }
}]

db.meterReads.aggregate(pipeline);
