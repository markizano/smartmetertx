#!/usr/bin/mongosh

/*

Upgrade meter reads in the DB.
Old structure:
datar:PRIMARY> db.meterReads.findOne()
{
	"_id" : ObjectId("60e73f0ebc5af4707082a051"),
	"tdspdunsno" : "1039940674000",
	"unitname" : "KWH",
	"startreading" : 16694.984,
	"endreading" : 16746.307,
	"reading" : 51.324,
	"errmsg" : "Success",
	"datetime" : ISODate("2019-07-09T12:00:00Z")
}

New data structure:
datar:PRIMARY> db.dailyReads.findOne()
{
	"_id" : ObjectId("66464b2a66da131fa3bfbeb1"),
	"readDate" : ISODate("2022-05-17T00:00:00Z"),
	"revisionDate" : ISODate("2022-05-18T06:30:15Z"),
	"startReading" : 72969.244,
	"endReading" : 73121.199,
	"energyDataKwh" : "151.954"
}

 */

function main() {
    const oldCollection = db.getCollection('meterReads');
    const newCollection = db.getCollection('dailyReads');
    const oldCursor = oldCollection.find().sort({ datetime: 1 });
    print(`Have ${oldCursor.count()} meter reads to upgrade.`);
    const meterReads = [];
    for ( var meterRead = oldCursor.next(); oldCursor.hasNext(); meterRead = oldCursor.next() ) {
        let dt = new Date(meterRead.datetime);
        dt.setUTCHours(0, 0, 0, 0);
        print(`Meter Date: ${meterRead.datetime}, Zeroed Date: ${dt}`);
        meterReads.push({
            readDate: dt,
            revisionDate: meterRead.datetime,
            startReading: meterRead.startreading,
            endReading: meterRead.endreading,
            energyDataKwh: meterRead.reading
        });
        // return 1;
    }

    print(`Found ${meterReads.length} meter reads to upgrade.`);
    const insertResult = newCollection.insertMany(meterReads, {ordered: false});
    printjson(insertResult);
    print("Upgrade completed.");
}

main();
