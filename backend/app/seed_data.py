import random
from datetime import datetime, timedelta
import json

from sqlalchemy.orm import Session

from .database import SessionLocal, engine, Base
from .models import Annotator, AnnotationTask, Annotation, Inspection, SamplingBatch, TaskStatus, ConsistencyStatus, InspectionResult


ANNOTATORS = [
    {"name": "标注员-李明", "avatar": None},
    {"name": "标注员-王芳", "avatar": None},
    {"name": "标注员-张伟", "avatar": None},
    {"name": "标注员-刘洋", "avatar": None},
    {"name": "标注员-陈静", "avatar": None},
    {"name": "标注员-赵强", "avatar": None},
]

SAMPLE_CONTENTS = [
    {
        "title": "商品标题审核-001",
        "content": "【正品保证】XX品牌手机壳 超薄透明防摔保护套 买一送一 限时特价",
        "content_type": "text",
    },
    {
        "title": "商品标题审核-002",
        "content": "全国包邮 纯棉T恤男士短袖夏季新款宽松半袖打底衫潮流ins上衣服",
        "content_type": "text",
    },
    {
        "title": "评论内容审核-001",
        "content": "这个产品真的太差了，完全是假货，建议大家不要买，客服态度也很恶劣",
        "content_type": "text",
    },
    {
        "title": "评论内容审核-002",
        "content": "物流超级快，包装很好，宝贝和描述一致，性价比很高，下次还会再来！",
        "content_type": "text",
    },
    {
        "title": "商品标题审核-003",
        "content": "【官方正品】XX精华液 美白淡斑补水保湿 买二送一 无效退款 月销10万+",
        "content_type": "text",
    },
    {
        "title": "直播弹幕审核-001",
        "content": "主播你好漂亮呀，求关注！我是你的老粉丝了~",
        "content_type": "text",
    },
    {
        "title": "直播弹幕审核-002",
        "content": "这东西这么贵还不如去抢钱，垃圾主播推荐垃圾货",
        "content_type": "text",
    },
    {
        "title": "商品详情页审核-001",
        "content": "【产品功效】28天淡化细纹，42天逆龄生长，医学界公认抗衰老神器，诺贝尔奖成分加持",
        "content_type": "text",
    },
    {
        "title": "用户昵称审核-001",
        "content": "中南海保镖_888",
        "content_type": "text",
    },
    {
        "title": "用户昵称审核-002",
        "content": "追风筝的人",
        "content_type": "text",
    },
    {
        "title": "商品标题审核-004",
        "content": "【假一赔十】XX运动鞋男款跑步鞋轻便透气跑鞋 专柜同款 支持验货",
        "content_type": "text",
    },
    {
        "title": "评论内容审核-003",
        "content": "收到货了，包装有点破损，但是东西没问题，整体还可以吧",
        "content_type": "text",
    },
    {
        "title": "评论内容审核-004",
        "content": "加微信xxxxxxx领取优惠券哦！更多惊喜等你来~",
        "content_type": "text",
    },
    {
        "title": "商品标题审核-005",
        "content": "【全网最低价】9.9元包邮 男士内裤冰丝平角裤 性感透气 今日秒杀",
        "content_type": "text",
    },
    {
        "title": "直播弹幕审核-003",
        "content": "666666主播太厉害了，这个价格真香！",
        "content_type": "text",
    },
    {
        "title": "用户头像描述审核-001",
        "content": "风景照片，海边日落",
        "content_type": "text",
    },
    {
        "title": "商品详情页审核-002",
        "content": "采用德国进口技术，航天级材料，经过10000次测试验证，使用寿命长达50年",
        "content_type": "text",
    },
    {
        "title": "评论内容审核-005",
        "content": "真的超好用，已经是第三次购买了，推荐给身边的朋友都说好",
        "content_type": "text",
    },
    {
        "title": "商品标题审核-006",
        "content": "XX品牌口红 不掉色不沾杯 持久滋润 孕妇可用 纯天然无添加",
        "content_type": "text",
    },
    {
        "title": "直播弹幕审核-004",
        "content": "关注主播，加入粉丝团，截屏抽奖送iPhone15！",
        "content_type": "text",
    },
]

LABEL_OPTIONS = {
    "risk_level": ["低风险", "中风险", "高风险"],
    "category": ["合规", "夸大宣传", "辱骂攻击", "引流广告", "敏感信息", "其他违规"],
    "suggestion": ["通过", "警告", "驳回", "封禁"],
}


def random_label(variation: float = 0.3) -> dict:
    labels = {
        "risk_level": random.choice(LABEL_OPTIONS["risk_level"]),
        "category": random.choice(LABEL_OPTIONS["category"]),
        "suggestion": random.choice(LABEL_OPTIONS["suggestion"]),
    }
    if random.random() < variation:
        key = random.choice(list(labels.keys()))
        original = labels[key]
        alternatives = [x for x in LABEL_OPTIONS[key] if x != original]
        if alternatives:
            labels[key] = random.choice(alternatives)
    return labels


def calc_consistency(result_a: dict, result_b: dict) -> tuple:
    matches = 0
    total = len(result_a)
    diff = {}
    for key in result_a:
        if result_a.get(key) == result_b.get(key):
            matches += 1
        else:
            diff[key] = {"a": result_a.get(key), "b": result_b.get(key)}
    score = matches / total if total > 0 else 0.0
    if score == 1.0:
        status = ConsistencyStatus.CONSISTENT
    elif score >= 0.5:
        status = ConsistencyStatus.PARTIAL
    else:
        status = ConsistencyStatus.INCONSISTENT
    return status, score, diff


def seed_data():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        annotators = []
        for a in ANNOTATORS:
            ann = Annotator(**a)
            db.add(ann)
            annotators.append(ann)
        db.flush()

        tasks = []
        for i, sc in enumerate(SAMPLE_CONTENTS):
            task = AnnotationTask(
                content_id=f"CONTENT-{i+1:04d}",
                title=sc["title"],
                content=sc["content"],
                content_type=sc["content_type"],
                status=TaskStatus.WAITING_INSPECTION,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
            )
            db.add(task)
            tasks.append(task)
        db.flush()

        for i, task in enumerate(tasks):
            ann_a, ann_b = random.sample(annotators, 2)
            result_a = random_label(variation=0)
            variation = random.choice([0.0, 0.3, 0.3, 0.6, 1.0])
            result_b = random_label(variation=variation)
            consistency_status, consistency_score, diff_detail = calc_consistency(result_a, result_b)

            annotation = Annotation(
                task_id=task.id,
                annotator_a_id=ann_a.id,
                annotator_b_id=ann_b.id,
                result_a=result_a,
                result_b=result_b,
                annotated_at_a=datetime.utcnow() - timedelta(days=random.randint(1, 10), hours=random.randint(0, 24)),
                annotated_at_b=datetime.utcnow() - timedelta(days=random.randint(1, 10), hours=random.randint(0, 24)),
                consistency_status=consistency_status,
                consistency_score=consistency_score,
                diff_detail=diff_detail,
            )
            db.add(annotation)

            if random.random() < 0.35:
                insp_result = random.choice([InspectionResult.PASS, InspectionResult.PASS, InspectionResult.FAIL, InspectionResult.ARBITRATED])
                final_ann = None
                if insp_result == InspectionResult.ARBITRATED:
                    final_ann = random_label(variation=0)
                inspection = Inspection(
                    task_id=task.id,
                    inspector_id=1,
                    inspector_name="质检员-孙丽",
                    result=insp_result,
                    final_annotation=final_ann,
                    comment={
                        InspectionResult.PASS: "双标注一致，结果正确，通过质检。",
                        InspectionResult.FAIL: "标注结果不准确，需重新标注。",
                        InspectionResult.ARBITRATED: "双标注存在分歧，已给出仲裁结果。",
                    }[insp_result],
                    score=random.randint(60, 100),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(0, 5)),
                )
                db.add(inspection)
                task.status = TaskStatus.COMPLETED

        db.flush()

        all_task_ids = [t.id for t in tasks]
        sample_size = min(10, len(all_task_ids))
        sampled = random.sample(all_task_ids, sample_size)
        batch1 = SamplingBatch(
            name="6月第一轮质检抽样",
            description="针对高风险和不一致的双标注结果进行抽样质检",
            sample_count=sample_size,
            strategy="random",
            consistency_filter=None,
            task_ids=sampled,
            created_by="质检员-孙丽",
        )
        db.add(batch1)

        sampled2 = random.sample(all_task_ids, min(5, len(all_task_ids)))
        batch2 = SamplingBatch(
            name="不一致结果专项抽检",
            description="只抽取标注结果不一致的任务进行重点质检",
            sample_count=len(sampled2),
            strategy="inconsistent_only",
            consistency_filter="inconsistent",
            task_ids=sampled2,
            created_by="质检员-孙丽",
        )
        db.add(batch2)

        db.commit()
        print("Seed data created successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
